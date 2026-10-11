"""Opt-in paid adapters. Disabled unless the operator supplies reviewed provider settings."""
import json
import os


def enabled_channels():
    channels = ['in-app', 'push', 'email']
    requested = os.environ.get('PAID_CHANNELS', '').split(',')
    if 'sms' in requested and all(os.environ.get(k) for k in ('SMS_ORIGINATION', 'SMS_CONFIG_SET', 'SMS_ENTITY_ID', 'SMS_TEMPLATE_ID')):
        channels.append('sms')
    if 'whatsapp' in requested and all(os.environ.get(k) for k in ('WHATSAPP_ORIGIN', 'WHATSAPP_TEMPLATE', 'META_API_VERSION')):
        channels.append('whatsapp')
    return channels


def send_sms(phone, event):
    if 'sms' not in enabled_channels():
        return 'not-configured'
    import boto3
    # Must exactly match the operator's registered DLT template. No freeform child data.
    message = f"Air Guardian: school planning flag {event['flag'].upper()}. Please review your school workspace."
    response = boto3.client('pinpoint-sms-voice-v2').send_text_message(
        DestinationPhoneNumber=phone, OriginationIdentity=os.environ['SMS_ORIGINATION'], MessageBody=message,
        MessageType='TRANSACTIONAL', ConfigurationSetName=os.environ['SMS_CONFIG_SET'],
        DestinationCountryParameters={'IN_ENTITY_ID': os.environ['SMS_ENTITY_ID'], 'IN_TEMPLATE_ID': os.environ['SMS_TEMPLATE_ID']},
        MaxPrice=os.environ.get('SMS_MAX_PRICE', '0.10'), TimeToLive=1800)
    return {'status': 'accepted-by-sms-service', 'providerId': response['MessageId']}


def send_whatsapp(phone, event):
    if 'whatsapp' not in enabled_channels():
        return 'not-configured'
    import boto3
    message = {'messaging_product': 'whatsapp', 'to': phone.lstrip('+'), 'type': 'template',
        'template': {'name': os.environ['WHATSAPP_TEMPLATE'], 'language': {'code': 'en'},
                     'components': [{'type': 'body', 'parameters': [{'type': 'text', 'text': event['flag'].upper()}]}]}}
    result = boto3.client('socialmessaging').send_whatsapp_message(originationPhoneNumberId=os.environ['WHATSAPP_ORIGIN'],
        message=json.dumps(message).encode(), metaApiVersion=os.environ['META_API_VERSION'])
    return {'status': 'accepted-by-whatsapp-service', 'providerId': result['messageId']}
