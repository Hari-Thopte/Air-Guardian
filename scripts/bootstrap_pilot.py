"""Bootstrap the configured campus after administrator signup and verified email."""
import argparse
import json
from aws_support import ROOT, outputs
from scripts.bootstrap_school import bootstrap
from cloud.contracts import school
from cloud.store import DynamoStore
import boto3

parser = argparse.ArgumentParser()
parser.add_argument('--stack', default='air-guardian-pilot')
parser.add_argument('--region', default='ap-south-1')
args = parser.parse_args()
boto3.setup_default_session(region_name=args.region)
session = boto3.Session(region_name=args.region)
values = outputs(session, args.stack)
pilot = json.loads((ROOT / 'deployment' / 'school.json').read_text())
user = session.client('cognito-idp').admin_get_user(UserPoolId=values['UserPoolId'], Username=pilot['admin_email'])
attrs = {r['Name']: r['Value'] for r in user['UserAttributes']}
if attrs.get('email_verified') != 'true' or not user.get('Enabled'):
    raise SystemExit('First sign up on the deployed website and verify the administrator email.')
if 'SOFTWARE_TOKEN_MFA' not in user.get('UserMFASettingList', []):
    raise SystemExit('Complete authenticator MFA enrollment at hosted login before bootstrap.')
bootstrap(DynamoStore(values['AppTableName']), school(pilot), attrs['sub'])
print('Campus and administrator linked. Sign in again, then create actual classes and private invitations in Enrollment.')
