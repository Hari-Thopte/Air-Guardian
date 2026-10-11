"""Provision secret material through hidden prompts; prints only public deployment parameters."""
import argparse
import base64
import getpass
import json
from aws_support import ROOT
import boto3

parser = argparse.ArgumentParser()
parser.add_argument('--region', default='ap-south-1')
parser.add_argument('--profile')
parser.add_argument('--provider', choices=['openaq', 'openweather', 'cpcb', 'waqi', 'iqair'])
parser.add_argument('--push', action='store_true')
parser.add_argument('--ses-email')
args = parser.parse_args()
session = boto3.Session(profile_name=args.profile, region_name=args.region)
if args.provider:
    key = getpass.getpass('Provider key (hidden): ').strip()
    if not key:
        raise SystemExit('Key must not be empty.')
    name = '/airguardian/providers/' + args.provider
    session.client('ssm').put_parameter(Name=name, Value=key, Type='SecureString', Overwrite=False)
    print(json.dumps({'ProviderParameters': json.dumps({args.provider: name})}))
if args.push:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    private = ec.generate_private_key(ec.SECP256R1())
    public = private.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    secret = base64.urlsafe_b64encode(private.private_bytes(
        serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())).decode().rstrip('=')
    path = '/airguardian/vapid/private'
    session.client('ssm').put_parameter(Name=path, Value=secret, Type='SecureString', Overwrite=False)
    print(json.dumps({'VapidPublicKey': base64.urlsafe_b64encode(public).decode().rstrip('='), 'VapidPrivateParameter': path}))
if args.ses_email:
    ses = session.client('sesv2')
    try:
        status = ses.get_email_identity(EmailIdentity=args.ses_email)
    except ses.exceptions.NotFoundException:
        ses.create_email_identity(EmailIdentity=args.ses_email)
        print('SES verification email requested. Complete it before setting SesFrom.')
    else:
        print(json.dumps({'senderVerified': status.get('VerifiedForSendingStatus', False),
                          'productionAccess': ses.get_account().get('ProductionAccessEnabled', False)}))
