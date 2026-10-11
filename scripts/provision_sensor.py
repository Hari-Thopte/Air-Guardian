"""Provision one already-registered experimental IoT device. Never prints private keys.

Certificate files are written under ignored .devices/<device-id>. Copy securely to
the device, then protect/remove the local copy. No broad wildcard device policy.
"""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cloud.contracts import identifier
from cloud.store import DynamoStore


def policy(account, region, device_id):
    return {'Version': '2012-10-17', 'Statement': [
        {'Effect': 'Allow', 'Action': 'iot:Connect', 'Resource': f'arn:aws:iot:{region}:{account}:client/{device_id}'},
        {'Effect': 'Allow', 'Action': 'iot:Publish', 'Resource': f'arn:aws:iot:{region}:{account}:topic/airguardian/{device_id}/telemetry'}]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', required=True)
    parser.add_argument('--table', required=True)
    parser.add_argument('--region', default='ap-south-1')
    args = parser.parse_args()
    did = identifier(args.device)
    os.environ['AWS_DEFAULT_REGION'] = args.region
    if not (DynamoStore(args.table).get('DEVICES', did) or {}).get('active'):
        raise SystemExit('Register the device through the school administrator first.')
    output = Path(__file__).resolve().parents[1] / '.devices' / did
    if output.exists():
        raise SystemExit('Device output directory already exists; refusing to overwrite keys.')
    output.mkdir(parents=True)
    import boto3
    client = boto3.client('iot')
    account = boto3.client('sts').get_caller_identity()['Account']
    cert = client.create_keys_and_certificate(setAsActive=False)
    (output / 'certificate.pem').write_text(cert['certificatePem'])
    (output / 'private-key.pem').write_text(cert['keyPair']['PrivateKey'])
    (output / 'certificate-id.txt').write_text(cert['certificateId'])
    client.create_thing(thingName=did)
    policy_name = 'airguardian-' + did
    client.create_policy(policyName=policy_name, policyDocument=json.dumps(policy(account, args.region, did)))
    client.attach_policy(policyName=policy_name, target=cert['certificateArn'])
    client.attach_thing_principal(thingName=did, principal=cert['certificateArn'])
    client.update_certificate(certificateId=cert['certificateId'], newStatus='ACTIVE')
    endpoint = client.describe_endpoint(endpointType='iot:Data-ATS')['endpointAddress']
    (output / 'device.json').write_text(json.dumps({'endpoint': endpoint, 'clientId': did, 'topic': f'airguardian/{did}/telemetry'}, indent=2))
    print('Provisioned one restricted device. Private material saved under .devices; never commit or share it.')
