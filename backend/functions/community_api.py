"""Local demo API using the real Powertools API Gateway event resolver.

Only the local preview imports this module. SQLite is local persistence, not
DynamoDB. Role selection is a demonstration, not staff authentication.
"""
import json
import re
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from backend.functions.air_engine import fetch_air, SCHOOLS
from backend.functions.guardian_rules import child_risk, AGE_GROUPS, recommendations
from backend.functions.guardian_api import router as guardian_router
from backend.functions.guardian_store import configured_school

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, ForbiddenError

app = APIGatewayRestResolver()
app.include_router(guardian_router,prefix='/api/guardian')
logger = Logger(service="airguardian-local", level="INFO")
DATABASE = Path(__file__).resolve().parents[1] / '.local' / 'plans.sqlite3'
SCENARIOS = {'good', 'moderate', 'poor', 'severe'}


@contextmanager
def connection():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE, timeout=5)
    db.execute('CREATE TABLE IF NOT EXISTS plans (school TEXT, scenario TEXT, body TEXT, PRIMARY KEY (school, scenario))')
    try:
        with db:
            yield db
    finally:
        db.close()


def validate(school):
    scenario = app.current_event.get_query_string_value('scenario', '')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', school) or scenario not in SCENARIOS:
        raise BadRequestError('Choose a valid school and demo scenario.')
    return scenario


def require_demo_staff():
    # This header is intentionally not an authentication mechanism. The server
    # binds only to loopback and rejects cross-origin writes.
    if app.current_event.headers.get('x-demo-role') != 'staff':
        raise ForbiddenError('Use the staff preview to change the demo plan.')


@app.get('/api/health')
def health():
    return {'mode': 'local-demo', 'project': 'Powertools for AWS Lambda (Python)',
            'storage': 'SQLite on this computer', 'cloudDeployed': False}


@app.get('/api/air/<school>')
def air_at_school(school):
    if school not in SCHOOLS:
        raise BadRequestError('Choose a configured school.')
    mode = app.current_event.get_query_string_value('mode', 'demo')
    if mode not in ('demo', 'live'):
        raise BadRequestError('Choose demo or live data.')
    age = app.current_event.get_query_string_value('age', '9-12')
    if age not in AGE_GROUPS:
        raise BadRequestError('Choose an age group.')
    result = fetch_air(configured_school(school), mode, app.current_event.get_query_string_value('polluted') == 'true')
    result['risk'] = child_risk(result, age, app.current_event.get_query_string_value('caution') == 'true')
    result['actions'] = recommendations(result,result['risk'])
    return result


@app.get('/api/plans/<school>')
def get_plan(school):
    scenario = validate(school)
    with connection() as db:
        row = db.execute('SELECT body FROM plans WHERE school = ? AND scenario = ?', (school, scenario)).fetchone()
    return {'plan': json.loads(row[0]) if row else None, 'mode': 'local-demo'}


@app.post('/api/plans/<school>')
def confirm_plan(school):
    scenario = validate(school)
    require_demo_staff()
    try:
        payload = app.current_event.json_body
    except (ValueError, TypeError):
        raise BadRequestError('A JSON object is required.')
    if not isinstance(payload, dict) or not isinstance(payload.get('note', ''), str) or len(payload.get('note', '')) > 300 or not isinstance(payload.get('caution', False), bool):
        raise BadRequestError('The school notice must be at most 300 characters.')
    plan = {'school': school, 'scenario': scenario, 'note': payload.get('note', '').strip(),
            'time': datetime.now(timezone.utc).isoformat(), 'shared': True,
            'caution': payload.get('caution', False)}
    with connection() as db:
        db.execute('INSERT INTO plans VALUES (?, ?, ?) ON CONFLICT(school, scenario) DO UPDATE SET body = excluded.body',
                   (school, scenario, json.dumps(plan)))
    logger.info('demo_plan_confirmed', extra={'scenario': scenario})
    return {'plan': plan, 'mode': 'local-demo'}


@app.delete('/api/plans/<school>')
def reopen_plan(school):
    scenario = validate(school)
    require_demo_staff()
    with connection() as db:
        db.execute('DELETE FROM plans WHERE school = ? AND scenario = ?', (school, scenario))
    logger.info('demo_plan_reopened', extra={'scenario': scenario})
    return {'plan': None, 'mode': 'local-demo'}


def handler(event, context):
    return app.resolve(event, context)
