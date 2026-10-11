"""Operator-only bootstrap. Does not create users, passwords, messages or fictional children."""
import argparse
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cloud.contracts import school
from cloud.store import DynamoStore, change


def bootstrap(store, config, subject):
    pk = 'SCHOOL#' + config['id']
    previous = store.get(pk, 'CONFIG')
    if previous and not previous.get('bootstrapPending'):
        raise ValueError('School exists; bootstrap will not overwrite it.')
    if previous and store.query(pk, 'MEMBER#'):
        raise ValueError('Pending school already has memberships; operator review required.')
    value = {k: v for k, v in previous.items() if k != 'bootstrapPending'} if previous else config
    index = store.get('SCHOOLS', pk)
    store.commit([change(pk, 'CONFIG', value, previous), change('SCHOOLS', pk, {'id': config['id']}, index),
        change(pk, 'MEMBER#' + subject, {'sub': subject, 'school': config['id'], 'role': 'admin', 'class_id': None, 'active': True}),
        change('USER#' + subject, pk, {'school': config['id']})])


def stage(store, config):
    """Initialize public school configuration for ingestion without granting anyone access."""
    pk = 'SCHOOL#' + config['id']
    if store.get(pk, 'CONFIG'):
        return False
    store.commit([change(pk, 'CONFIG', dict(config, bootstrapPending=True)),
                  change('SCHOOLS', pk, {'id': config['id']})])
    return True


if __name__ == '__main__':
    deps = Path(__file__).resolve().parents[1] / '.test-output' / 'deps'
    if deps.exists():
        sys.path.insert(0, str(deps))
    parser = argparse.ArgumentParser()
    for name in ('table', 'pool', 'admin-email', 'school-id', 'name', 'lat', 'lon'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--region', default='ap-south-1')
    args = parser.parse_args()
    import boto3
    user = boto3.client('cognito-idp', region_name=args.region).admin_get_user(UserPoolId=args.pool, Username=args.admin_email)
    attrs = {r['Name']: r['Value'] for r in user['UserAttributes']}
    if attrs.get('email_verified') != 'true' or not user.get('Enabled'):
        raise ValueError('Administrator must first sign up and verify their email.')
    os.environ['AWS_DEFAULT_REGION'] = args.region
    config = school({'id': args.school_id, 'name': args.name, 'lat': float(args.lat), 'lon': float(args.lon)})
    bootstrap(DynamoStore(args.table), config, attrs['sub'])
    print('School created and verified administrator linked. No messages were sent.')
