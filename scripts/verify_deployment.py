"""Read-only AWS configuration evidence. Does not claim live delivery or workflow success."""
import argparse
import json
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from aws_support import ROOT, outputs
import boto3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stack', default='air-guardian-pilot')
    parser.add_argument('--region', default='ap-south-1')
    parser.add_argument('--profile')
    args = parser.parse_args()
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    values = outputs(session, args.stack)
    checks = []
    def record(name, passed, detail):
        checks.append({'check': name, 'passed': bool(passed), 'detail': detail})
    resources = [r for page in session.client('cloudformation').get_paginator('list_stack_resources').paginate(StackName=args.stack)
                 for r in page['StackResourceSummaries']]
    for resource in resources:
        kind, physical = resource['ResourceType'], resource.get('PhysicalResourceId')
        if kind == 'AWS::Lambda::Function':
            cfg = session.client('lambda').get_function_configuration(FunctionName=physical)
            record(resource['LogicalResourceId'], cfg['Runtime'] == 'python3.12' and cfg.get('Architectures') == ['arm64'] and cfg['State'] == 'Active',
                   {'runtime': cfg['Runtime'], 'architecture': cfg.get('Architectures'), 'state': cfg['State']})
        elif kind == 'AWS::Scheduler::Schedule':
            cfg = session.client('scheduler').get_schedule(Name=physical.split('/')[-1])
            record(resource['LogicalResourceId'], cfg['State'] == 'ENABLED' and bool(cfg['Target'].get('DeadLetterConfig')),
                   {'state': cfg['State'], 'expression': cfg['ScheduleExpression'], 'retries': cfg['Target'].get('RetryPolicy')})
        elif kind == 'AWS::CloudWatch::Alarm':
            cfg = session.client('cloudwatch').describe_alarms(AlarmNames=[physical])['MetricAlarms'][0]
            record(resource['LogicalResourceId'], cfg.get('ActionsEnabled') and values['OperationsTopicArn'] in cfg.get('AlarmActions', []),
                   {'state': cfg['StateValue'], 'note': 'Configuration check; alarm receipt must be tested separately.'})
        elif kind == 'AWS::Budgets::Budget':
            account_id = session.client('sts').get_caller_identity()['Account']
            cfg = session.client('budgets').describe_budget(AccountId=account_id, BudgetName=physical)['Budget']
            notifications = session.client('budgets').describe_notifications_for_budget(AccountId=account_id, BudgetName=physical)['Notifications']
            record('Monthly cost alert', float(cfg['BudgetLimit']['Amount']) == 10 and bool(notifications),
                   {'amount': cfg['BudgetLimit']['Amount'], 'unit': cfg['BudgetLimit']['Unit'], 'notifications': len(notifications)})
    if values.get('WebBucketName') and values.get('DistributionId'):
        public_access = session.client('s3').get_public_access_block(Bucket=values['WebBucketName'])['PublicAccessBlockConfiguration']
        record('Private S3 origin', all(public_access.values()), public_access)
        distribution = session.client('cloudfront').get_distribution(Id=values['DistributionId'])['Distribution']
        record('CloudFront deployed', distribution['Status'] == 'Deployed', distribution['Status'])
    else:
        record('CloudFront deployed', False, 'Awaiting AWS account verification; backend-only deployment.')
    pool = session.client('cognito-idp').describe_user_pool(UserPoolId=values['UserPoolId'])['UserPool']
    record('MFA required', pool.get('MfaConfiguration') == 'ON', pool.get('MfaConfiguration'))
    subs = session.client('sns').list_subscriptions_by_topic(TopicArn=values['OperationsTopicArn'])['Subscriptions']
    record('Alarm subscriber confirmed', any(s['SubscriptionArn'].startswith('arn:') for s in subs),
           {'confirmed': sum(s['SubscriptionArn'].startswith('arn:') for s in subs), 'pending': sum(s['SubscriptionArn'] == 'PendingConfirmation' for s in subs)})
    attrs = session.client('sqs').get_queue_attributes(QueueUrl=values['DeliveryQueueUrl'], AttributeNames=['RedrivePolicy', 'VisibilityTimeout'])['Attributes']
    record('Delivery retries configured', bool(attrs.get('RedrivePolicy')) and int(attrs.get('VisibilityTimeout', 0)) >= 720, attrs)
    mappings = session.client('lambda').list_event_source_mappings(EventSourceArn=session.client('sqs').get_queue_attributes(
        QueueUrl=values['DeliveryQueueUrl'], AttributeNames=['QueueArn'])['Attributes']['QueueArn'])['EventSourceMappings']
    record('Queue processing enabled', any(m['State'] == 'Enabled' and 'ReportBatchItemFailures' in m.get('FunctionResponseTypes', []) for m in mappings),
           [{'state': m['State']} for m in mappings])
    if values['Website'].startswith('https://'):
        try:
            with urlopen(values['Website'] + '/cloud.html', timeout=30) as response:
                record('HTTPS website', response.status == 200, response.status)
        except Exception as error:
            record('HTTPS website', False, type(error).__name__)
    else:
        record('HTTPS website', False, 'Only a localhost test origin is configured.')
    # A protected ANY route must not require JWTs on browser preflight requests.
    origin = values['Website'].rstrip('/')
    try:
        with urlopen(Request(values['ApiUrl'] + '/v1/session', method='OPTIONS', headers={
                'Origin': origin, 'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'authorization,content-type'}), timeout=20) as response:
            allowed = response.headers.get('Access-Control-Allow-Origin')
            record('Browser preflight allowed', response.status in (200, 204) and allowed == origin,
                   {'status': response.status, 'origin': allowed})
    except Exception as error:
        record('Browser preflight allowed', False, type(error).__name__)
    try:
        with urlopen(Request(values['ApiUrl'] + '/v1/session'), timeout=20) as response:
            record('Anonymous access denied', False, response.status)
    except Exception as error:
        from urllib.error import HTTPError
        record('Anonymous access denied', isinstance(error, HTTPError) and error.code in (401, 403), type(error).__name__)
    school = json.loads((ROOT / 'deployment' / 'school.json').read_text())
    from cloud.store import DynamoStore
    import os
    os.environ['AWS_DEFAULT_REGION'] = args.region
    if args.profile:
        boto3.setup_default_session(profile_name=args.profile, region_name=args.region)
    current = DynamoStore(values['AppTableName']).get('SCHOOL#' + school['id'], 'CURRENT')
    import time
    record('School ingestion fresh', current and time.time() - current.get('lastSuccessfulAt', 0) < 1800,
           {'lastSuccessfulAt': (current or {}).get('lastSuccessfulAt'), 'note': 'Requires school bootstrap and an observed scheduled run.'})
    report = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'stack': args.stack, 'checks': checks,
              'manualEvidenceRequired': ['actual alarm email receipt', 'opted-in channel delivery', 'publish/acknowledge/review',
                                         'cross-school denial', 'forecast observation evaluation', 'hardware calibration', 'demo recording']}
    target = ROOT / '.test-output' / 'deployment-verification.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding='utf-8')
    for check in checks:
        print(('PASS' if check['passed'] else 'PENDING/FAIL') + ': ' + check['check'])
    print('Evidence:', target)
    return int(any(not check['passed'] for check in checks))


if __name__ == '__main__':
    raise SystemExit(main())
