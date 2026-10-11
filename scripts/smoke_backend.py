"""Live operator smoke: real ingestion/DynamoDB and a queue job with no recipient.

The API handler invocation uses IAM, not an end-user JWT, and does not establish login.
"""
import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from aws_support import ROOT, outputs
from cloud.store import DynamoStore
from cloud.pipeline import history
import boto3
from botocore.config import Config

parser = argparse.ArgumentParser()
parser.add_argument('--stack', default='air-guardian-pilot')
parser.add_argument('--region', default='ap-south-1')
args = parser.parse_args()
boto3.setup_default_session(region_name=args.region)
session = boto3.Session(region_name=args.region)
values = outputs(session, args.stack)
resources = {r['LogicalResourceId']: r['PhysicalResourceId'] for p in
             session.client('cloudformation').get_paginator('list_stack_resources').paginate(StackName=args.stack)
             for r in p['StackResourceSummaries']}
client = session.client('lambda', config=Config(read_timeout=360, retries={'max_attempts': 0}))
checks = []
def invoke(logical, event):
    response = client.invoke(FunctionName=resources[logical], InvocationType='RequestResponse', Payload=json.dumps(event).encode())
    payload = json.loads(response['Payload'].read())
    passed = not response.get('FunctionError')
    checks.append({'check': logical + ' live invocation', 'passed': passed,
                   'detail': payload if passed else {'functionError': response['FunctionError'], 'errorType': payload.get('errorType')}})
    print(('PASS' if passed else 'FAIL') + ': ' + logical, flush=True)
    return payload, passed
subject = 'operator-probe-' + str(uuid.uuid4())
payload, passed = invoke('ApiFunction', {'requestContext': {'authorizer': {'jwt': {'claims': {'sub': subject, 'token_use': 'access'}}},
                                          'http': {'method': 'GET'}}, 'rawPath': '/v1/session'})
checks.append({'check': 'API handler real DynamoDB read', 'passed': passed and payload.get('statusCode') == 200,
               'detail': 'IAM invocation with synthetic gateway envelope; end-user authentication remains untested.'})
invoke('IngestionFunction', {})
school = json.loads((ROOT / 'deployment' / 'school.json').read_text())
store = DynamoStore(values['AppTableName'])
current = store.get('SCHOOL#' + school['id'], 'CURRENT') or {}
air = current.get('air') or {}
checks.append({'check': 'Real provider state persisted', 'passed': bool(current.get('lastSuccessfulAt') and air.get('pm25') is not None and not air.get('stale')),
               'detail': {k: air.get(k) for k in ('source', 'observedAt', 'pm25', 'pm10', 'mode', 'method')}})
observations = history(DynamoStore(values['ReadingsTableName']), school['id'], 1)['readings']
checks.append({'check': 'Real provider history persisted', 'passed': bool(observations),
               'detail': {'samples': len(observations), 'sources': sorted({r['source'] for r in observations})}})
invoke('RelayFunction', {})
if store.get('SCHOOL#' + school['id'], 'MEMBER#' + subject):
    raise SystemExit('Refusing queue test: probe recipient unexpectedly exists.')
sqs = session.client('sqs')
probe = {
    'school': school['id'], 'sub': subject, 'event': {'school': school['id'], 'id': subject,
    'kind': 'operator-smoke', 'time': time.time(), 'expiresAt': time.time() + 90, 'flag': 'unknown', 'mode': 'live'}}
delivery, passed = invoke('DeliveryFunction', {'Records': [{'messageId': subject, 'body': json.dumps(probe)}]})
checks.append({'check': 'Delivery handler accepts safe no-recipient probe', 'passed': passed and delivery.get('batchItemFailures') == [],
               'detail': 'Actual Lambda invocation; no recipient membership or contact exists.'})
message = sqs.send_message(QueueUrl=values['DeliveryQueueUrl'], MessageBody=json.dumps(probe))
# Avoid treating the eventual queue counters' initial zero as proof of consumption.
time.sleep(15)
drained = False
for _ in range(12):
    attrs = sqs.get_queue_attributes(QueueUrl=values['DeliveryQueueUrl'], AttributeNames=[
        'ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible'])['Attributes']
    if all(int(v) == 0 for v in attrs.values()):
        drained = True
        break
    time.sleep(5)
checks.append({'check': 'SQS probe drained', 'passed': drained,
               'detail': {'messageId': message['MessageId'], 'note': 'No membership/contact exists for the recipient; no external delivery requested. Queue counters are approximate.'}})
report = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'stack': args.stack, 'checks': checks,
          'notVerified': ['public CloudFront hosting', 'real user login', 'human alarm receipt', 'teacher/parent workflow', 'external message receipt']}
target = ROOT / '.test-output' / 'live-backend-smoke.json'
target.write_text(json.dumps(report, indent=2), encoding='utf-8')
for check in checks:
    print(('PASS' if check['passed'] else 'FAIL') + ': ' + check['check'])
print('Evidence:', target)
raise SystemExit(int(any(not c['passed'] for c in checks)))
