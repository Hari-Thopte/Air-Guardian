"""Initialize configured campus for ingestion. No users, memberships or class rosters."""
import argparse
import json
from aws_support import ROOT, outputs
from scripts.bootstrap_school import stage
from cloud.contracts import school
from cloud.store import DynamoStore
import boto3

parser = argparse.ArgumentParser()
parser.add_argument('--stack', default='air-guardian-pilot')
parser.add_argument('--region', default='ap-south-1')
args = parser.parse_args()
boto3.setup_default_session(region_name=args.region)
values = outputs(boto3.Session(region_name=args.region), args.stack)
config = school(json.loads((ROOT / 'deployment' / 'school.json').read_text()))
created = stage(DynamoStore(values['AppTableName']), config)
print('Campus initialized for ingestion; administrator verification pending.' if created else 'Existing campus preserved.')
