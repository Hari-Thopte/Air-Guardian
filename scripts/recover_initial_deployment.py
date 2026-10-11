"""Recover only an empty failed initial pilot. Refuses populated or successful stacks."""
import argparse
from datetime import timezone
from aws_support import ROOT
import boto3

parser = argparse.ArgumentParser()
parser.add_argument('--stack', default='air-guardian-pilot')
parser.add_argument('--region', default='ap-south-1')
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()
session = boto3.Session(region_name=args.region)
cf = session.client('cloudformation')
stack = cf.describe_stacks(StackName=args.stack)['Stacks'][0]
if stack['StackStatus'] != 'ROLLBACK_COMPLETE':
    raise SystemExit('Refusing recovery: stack must be a failed initial creation in ROLLBACK_COMPLETE.')
resources = [r for p in cf.get_paginator('list_stack_resources').paginate(StackName=args.stack) for r in p['StackResourceSummaries']]
if any(r['ResourceType'] == 'AWS::Lambda::Function' and r.get('PhysicalResourceId') for r in resources):
    raise SystemExit('Refusing automatic cleanup: Lambda resources exist; review stack and data manually.')
plans = []
for r in resources:
    if r['ResourceStatus'] != 'DELETE_SKIPPED':
        continue
    logical, physical, kind = r['LogicalResourceId'], r['PhysicalResourceId'], r['ResourceType']
    if logical in ('AppTable', 'ReadingsTable') and kind == 'AWS::DynamoDB::Table':
        client = session.client('dynamodb')
        table = client.describe_table(TableName=physical)['Table']
        if table['CreationDateTime'] < stack['CreationTime'] or client.scan(TableName=physical, Limit=1, ConsistentRead=True).get('Items'):
            raise SystemExit('Refusing cleanup: table predates stack or contains records.')
        plans.append((logical, client.delete_table, {'TableName': physical}))
    elif logical == 'UserPool' and kind == 'AWS::Cognito::UserPool':
        client = session.client('cognito-idp')
        pool = client.describe_user_pool(UserPoolId=physical)['UserPool']
        if pool['CreationDate'] < stack['CreationTime'] or client.list_users(UserPoolId=physical, Limit=1).get('Users'):
            raise SystemExit('Refusing cleanup: user pool predates stack or contains users.')
        plans.append((logical, client.delete_user_pool, {'UserPoolId': physical}))
    elif logical == 'WebBucket' and kind == 'AWS::S3::Bucket':
        client = session.client('s3')
        if client.list_objects_v2(Bucket=physical, MaxKeys=1).get('Contents') or client.list_object_versions(Bucket=physical, MaxKeys=1).get('Versions'):
            raise SystemExit('Refusing cleanup: website bucket contains objects.')
        plans.append((logical, client.delete_bucket, {'Bucket': physical}))
    else:
        raise SystemExit('Refusing cleanup of unexpected retained resource: ' + logical)
for logical, _, kwargs in plans:
    print('Verified empty:', logical, list(kwargs.values())[0])
if not args.execute:
    print('Review-only. Add --execute to delete these empty failed-creation resources and stack record.')
    raise SystemExit(0)
for logical, delete, kwargs in plans:
    delete(**kwargs)
    print('Removed empty failed-creation resource:', logical)
cf.delete_stack(StackName=args.stack)
cf.get_waiter('stack_delete_complete').wait(StackName=args.stack)
print('Failed initial stack removed. No populated resource was deleted.')
