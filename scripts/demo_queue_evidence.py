"""One real SQS-to-Lambda notification for the verified pilot admin; in-app only.

Never changes preferences or contacts. A durable delivery receipt, rather than
approximate queue counts, establishes that the event-source consumer processed it.
"""
import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from aws_support import ROOT, outputs
from cloud.contracts import DEFAULT_PREFS
from cloud.store import DynamoStore, public
import boto3

parser = argparse.ArgumentParser()
parser.add_argument('--stack', default='air-guardian-pilot')
parser.add_argument('--region', default='ap-south-1')
args = parser.parse_args()
boto3.setup_default_session(region_name=args.region)
session = boto3.Session(region_name=args.region)
values = outputs(session, args.stack)
pilot = json.loads((ROOT / 'deployment' / 'school.json').read_text())
user = session.client('cognito-idp').admin_get_user(
    UserPoolId=values['UserPoolId'], Username=pilot['admin_email'])
attrs = {r['Name']: r['Value'] for r in user['UserAttributes']}
if attrs.get('email_verified') != 'true' or 'SOFTWARE_TOKEN_MFA' not in user.get('UserMFASettingList', []):
    raise SystemExit('Verified administrator email and active authenticator required.')
store = DynamoStore(values['AppTableName'])
sid, sub = pilot['id'], attrs['sub']
member = store.get('SCHOOL#' + sid, 'MEMBER#' + sub)
if not member or not member.get('active') or member.get('role') != 'admin':
    raise SystemExit('Configured administrator membership required.')
prefs = {**DEFAULT_PREFS, **(store.get('USER#' + sub, 'PREFERENCES') or {})}
if prefs['channels'] != ['in-app']:
    raise SystemExit('Refusing: this demo requires existing in-app-only preferences.')
current = store.get('SCHOOL#' + sid, 'CURRENT') or {}
air = current.get('air') or {}
if air.get('stale') or air.get('pm25') is None or time.time() - current.get('lastSuccessfulAt', 0) > 1800:
    raise SystemExit('Fresh persisted real air required; run smoke_backend.py first.')
now = time.time()
eid = 'aws-demo-' + str(uuid.uuid4())
event = {'id': eid, 'school': sid, 'kind': 'operator-smoke', 'time': now,
         'expiresAt': now + 3600, 'mode': 'live',
         'flag': current['planning']['flag'], 'audience': [{'sub': sub}]}
result = session.client('sqs').send_message(QueueUrl=values['DeliveryQueueUrl'],
    MessageBody=json.dumps({'school': sid, 'sub': sub, 'event': event}))
print('SQS message accepted:', result['MessageId'], flush=True)
key = f'DELIVERY#{sid}#{now:016.3f}#{eid}#in-app#in-app'
receipt = None
for _ in range(24):
    receipt = store.get('USER#' + sub, key)
    if receipt and receipt.get('status') not in ('pending', 'failed'):
        break
    time.sleep(5)
passed = bool(receipt and receipt.get('status') == 'in-app')
report = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'stack': args.stack,
          'school': sid, 'api': values['ApiUrl'], 'website': values['Website'] + '/cloud.html',
          'air': {k: air.get(k) for k in ('source', 'observedAt', 'pm25', 'pm10', 'method', 'mode')},
          'sqs': {'queueUrl': values['DeliveryQueueUrl'], 'messageId': result['MessageId'],
                  'eventId': eid, 'kind': event['kind']},
          'delivery': {'passed': passed, 'receipt': public(receipt) if receipt else None,
                       'proof': 'Durable receipt written by the real SQS-triggered delivery Lambda.'},
          'externalDeliveryRequested': False,
          'note': 'Browser Cognito login and displayed values are verified separately through the UI.'}
target = ROOT / '.test-output' / 'demo-queue-evidence.json'
target.write_text(json.dumps(public(report), indent=2), encoding='utf-8')
print(('PASS' if passed else 'FAIL') + ': real SQS-triggered in-app notification receipt')
print('Evidence:', target)
raise SystemExit(int(not passed))
