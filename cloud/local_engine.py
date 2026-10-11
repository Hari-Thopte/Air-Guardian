"""Credential-free Powertools Lambda slice. Fictional data only; no school access."""
import json
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from backend.functions.air_engine import demo
from cloud.contracts import school
from cloud.policy import plan
from cloud.dayplan import presentation

logger = Logger(service='air-guardian-local-engine')
app = APIGatewayRestResolver()


@app.get('/engine')
def engine():
    config = school({'id':'example','name':'Fictional school','lat':28.6139,'lon':77.209})
    air = demo(config, True)
    planning = plan(air, config)
    return {'label':'Demo data. Not live measurements.', 'awsOpenSource':'Powertools for AWS Lambda (Python)',
            'planning':planning, 'dayPlan':presentation(config, planning)}


@logger.inject_lambda_context(log_event=False)
def handler(event, context):
    return app.resolve(event, context)
