"""Access-token-authorized account operations; no operator credentials or phone overrides."""
import re
from cloud.contracts import Problem
from cloud.rate_limit import reserve
from cloud.store import change


def account(store, subject, token, method, path, data, client=None):
    if not token:
        raise Problem('Access token required.', 401)
    if client is None:
        import boto3
        client = boto3.client('cognito-idp')
    try:
        user = client.get_user(AccessToken=token)
    except Exception as error:
        if getattr(error, 'response', {}).get('Error', {}).get('Code') == 'NotAuthorizedException':
            raise Problem('Sign in again to manage your account.', 401) from None
        raise Problem('Account verification is temporarily unavailable.', 503) from None
    attrs = {a['Name']: a['Value'] for a in user['UserAttributes']}
    if attrs.get('sub') != subject:
        raise Problem('Account identity does not match.', 403)
    if method == 'GET' and path == '/v1/account':
        return {'phone': attrs.get('phone_number', ''),
                'phoneVerified': attrs.get('phone_number_verified') == 'true',
                'mfaEnabled': 'SOFTWARE_TOKEN_MFA' in user.get('UserMFASettingList', [])}
    if method != 'POST':
        raise Problem('Method not supported.', 405)
    if path not in ('/v1/account/phone', '/v1/account/phone/resend', '/v1/account/phone/verify'):
        raise Problem('Route not found.', 404)
    for link in store.query('USER#' + subject, 'SCHOOL#'):
        membership = store.get('SCHOOL#' + link['school'], 'MEMBER#' + subject) or {}
        if membership.get('active') and membership.get('role') == 'kid':
            raise Problem('Kid accounts cannot enroll phone contacts.', 403)
    reserve(store, subject, 'phone', cap=3, period=300)
    try:
        if path.endswith('/verify'):
            code = str(data.get('code', ''))
            if not re.fullmatch(r'\d{6}', code):
                raise Problem('Enter the six-digit verification code.')
            client.verify_user_attribute(AccessToken=token, AttributeName='phone_number', Code=code)
            return {'verified': True, 'note': 'Save notification preferences again to consent to phone delivery.'}
        if path == '/v1/account/phone':
            phone = data.get('phone', '')
            if not isinstance(phone, str) or not re.fullmatch(r'\+[1-9]\d{7,14}', phone):
                raise Problem('Enter a phone number with country code, such as +919876543210.')
            contact = store.get('USER#' + subject, 'CONTACT')
            if contact and contact.get('phone'):
                updated = {k: v for k, v in contact.items() if k != 'phone'}
                store.commit([change('USER#' + subject, 'CONTACT', updated, contact)])
            client.update_user_attributes(AccessToken=token, UserAttributes=[{'Name': 'phone_number', 'Value': phone}])
        result = client.get_user_attribute_verification_code(AccessToken=token, AttributeName='phone_number')
        return {'sent': True, 'destination': result.get('CodeDeliveryDetails', {}).get('Destination', '')}
    except Problem:
        raise
    except Exception as error:
        code = getattr(error, 'response', {}).get('Error', {}).get('Code', '')
        if code in ('CodeMismatchException', 'ExpiredCodeException'):
            raise Problem('The verification code is invalid or expired. Request a new code.') from None
        if code in ('LimitExceededException', 'TooManyRequestsException'):
            raise Problem('Verification limit reached. Wait before trying again.', 429) from None
        if code == 'NotAuthorizedException':
            raise Problem('Sign in again to manage your account.', 401) from None
        raise Problem('Phone verification is unavailable. The operator must configure Cognito SMS delivery.', 503) from None
