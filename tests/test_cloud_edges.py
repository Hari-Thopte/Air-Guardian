import json
import os
import time
import unittest
from unittest.mock import patch
from cloud import api
from cloud.channels import enabled_channels, send_sms, send_whatsapp
from cloud.feedback import parse, apply_feedback
from cloud.store import MemoryStore, change
from cloud.privacy import erase_private
from cloud.notifications import deliver
from cloud.contracts import school, DEFAULT_PREFS, Problem
from scripts.bootstrap_school import bootstrap


class BoundaryTests(unittest.TestCase):
    def test_preflight_is_empty_and_never_opens_private_store(self):
        with patch('cloud.api.DynamoStore', side_effect=AssertionError('No store access')):
            result = api.handler({'requestContext': {'http': {'method': 'OPTIONS'}},
                                  'rawPath': '/v1/session'}, None)
        self.assertEqual(result['statusCode'], 204)
        self.assertEqual(result['body'], '')

    def test_school_preserves_provider_and_assessment_context(self):
        value = school({'id': 'test', 'name': 'Test school', 'lat': 19, 'lon': 72,
                        'cpcb_city': 'Mumbai', 'outdoor_area_score': 3})
        self.assertEqual(value['cpcb_city'], 'Mumbai')
        self.assertEqual(value['outdoor_area_score'], 3)
        with self.assertRaises(Problem):
            school(dict(value, outdoor_area_score=6))

    def test_unrecognized_sms_event_does_not_claim_failure(self):
        self.assertEqual(parse({'eventType': 'TEXT_NEW_STATUS', 'messageId': 'test'}), [])

    def test_provider_quota_reserves_failed_attempt_budget(self):
        from cloud.providers import reserve_requests
        store = MemoryStore()
        reserve_requests(store, 'example', cost=2, limit=3)
        with self.assertRaises(Problem):
            reserve_requests(store, 'example', cost=2, limit=3)
        reserve_requests(store, 'example', cost=1, limit=3)

    def test_device_policy_has_no_wildcard_or_cross_device_publish(self):
        from scripts.provision_sensor import policy
        value = policy('123456789012', 'ap-south-1', 'gate-one')
        self.assertNotIn('*', json.dumps(value))
        self.assertEqual(value['Statement'][1]['Resource'],
                         'arn:aws:iot:ap-south-1:123456789012:topic/airguardian/gate-one/telemetry')

    def test_gateway_claims_required_even_with_role_headers(self):
        result = api.handler({'headers': {'x-demo-role': 'admin'}, 'rawPath': '/v1/session'}, None)
        self.assertEqual(result['statusCode'], 401)

    def test_id_token_is_not_accepted_as_api_access_token(self):
        event = {'requestContext': {'authorizer': {'jwt': {'claims': {'sub': 'abc', 'token_use': 'id'}}}}}
        self.assertEqual(api.handler(event, None)['statusCode'], 401)

    def test_paid_channels_disabled_without_complete_configuration(self):
        with patch.dict(os.environ, {'PAID_CHANNELS': ''}):
            self.assertNotIn('sms', enabled_channels())
            self.assertEqual(send_sms('+919000000000', {'flag': 'red'}), 'not-configured')
            self.assertEqual(send_whatsapp('+919000000000', {'flag': 'red'}), 'not-configured')

    def test_sms_adapter_uses_registered_template_and_price_limit(self):
        import boto3
        from botocore.stub import Stubber
        env = {'PAID_CHANNELS': 'sms', 'SMS_ORIGINATION': 'sender-id-test', 'SMS_CONFIG_SET': 'airguardian',
               'SMS_ENTITY_ID': 'entity1', 'SMS_TEMPLATE_ID': 'template1', 'SMS_MAX_PRICE': '0.10'}
        client = boto3.client('pinpoint-sms-voice-v2', region_name='ap-south-1', aws_access_key_id='test', aws_secret_access_key='test')
        with patch.dict(os.environ, env), Stubber(client) as stub:
            stub.add_response('send_text_message', {'MessageId': 'msg1'}, {
                'DestinationPhoneNumber': '+919000000000', 'OriginationIdentity': 'sender-id-test',
                'MessageBody': 'Air Guardian: school planning flag RED. Please review your school workspace.',
                'MessageType': 'TRANSACTIONAL', 'ConfigurationSetName': 'airguardian',
                'DestinationCountryParameters': {'IN_ENTITY_ID': 'entity1', 'IN_TEMPLATE_ID': 'template1'},
                'MaxPrice': '0.10', 'TimeToLive': 1800})
            with patch('boto3.client', return_value=client):
                self.assertEqual(send_sms('+919000000000', {'flag': 'red'})['providerId'], 'msg1')

    def test_whatsapp_adapter_uses_template_not_freeform_child_data(self):
        import boto3
        from botocore.stub import Stubber, ANY
        client = boto3.client('socialmessaging', region_name='ap-south-1', aws_access_key_id='test', aws_secret_access_key='test')
        env = {'PAID_CHANNELS': 'whatsapp', 'WHATSAPP_ORIGIN': 'phone-number-id-test', 'WHATSAPP_TEMPLATE': 'school_air', 'META_API_VERSION': 'v23.0'}
        with patch.dict(os.environ, env), Stubber(client) as stub:
            stub.add_response('send_whatsapp_message', {'messageId': 'wamid.test'},
                              {'originationPhoneNumberId': 'phone-number-id-test', 'message': ANY, 'metaApiVersion': 'v23.0'})
            with patch('boto3.client', return_value=client):
                self.assertEqual(send_whatsapp('+919000000000', {'flag': 'red', 'child': 'Never sent'})['providerId'], 'wamid.test')

    def test_feedback_parser_handles_aws_whatsapp_envelope(self):
        payload = {'whatsAppWebhookEntry': json.dumps({'changes': [{'value': {'statuses': [{'id': 'wamid.1', 'status': 'read'}]}}]})}
        self.assertEqual(parse(payload), [('whatsapp', 'wamid.1', 'read')])
        self.assertEqual(parse({'eventType': 'TEXT_DELIVERED', 'messageId': 'sms1'}), [('sms', 'sms1', 'delivered')])

    def test_feedback_never_regresses_read_to_sent(self):
        store = MemoryStore()
        store.commit([change('USER#p', 'delivery', {'status': 'read'}),
                      change('PROVIDER_MESSAGES', 'whatsapp#id', {'pk': 'USER#p', 'sk': 'delivery'})])
        apply_feedback(store, 'whatsapp', 'id', 'sent')
        self.assertEqual(store.get('USER#p', 'delivery')['status'], 'read')

    def test_bounced_email_suppresses_further_sends(self):
        store = MemoryStore()
        store.commit([change('USER#p', 'delivery', {'status': 'accepted-by-email-service'}),
                      change('USER#p', 'CONTACT', {'email': 'test@example.invalid'}),
                      change('PROVIDER_MESSAGES', 'email#id', {'pk': 'USER#p', 'sk': 'delivery'})])
        apply_feedback(store, 'email', 'id', 'bounced')
        self.assertTrue(store.get('USER#p', 'CONTACT')['emailSuppressed'])

    def test_erasure_job_recovers_after_membership_has_already_been_removed(self):
        store = MemoryStore()
        job = {'school': 's', 'sub': 'p'}
        store.commit([change('ERASURE', 's#p', job), change('USER#p', 'CHECKIN#s#kid#day', {'signal': True}),
                      change('USER#p', 'CONTACT', {'email': 'test@example.invalid'}),
                      change('USER#p', 'PUSH#1', {'subscription': {}})])
        erase_private(store, job)
        self.assertEqual(store.query('USER#p'), [])
        self.assertIsNone(store.get('ERASURE', 's#p'))

    def test_quiet_hours_suppress_external_channel(self):
        store = MemoryStore(); now = time.time()
        config = school({'id': 's', 'name': 'Fictional', 'lat': 0, 'lon': 0, 'timezone': 'UTC'})
        bootstrap(store, config, 'p')
        # Make the entire current minute a quiet interval without relying on the host timezone.
        from datetime import datetime, timezone, timedelta
        start = datetime.fromtimestamp(now, timezone.utc).strftime('%H:%M')
        end = (datetime.fromtimestamp(now, timezone.utc) + timedelta(minutes=1)).strftime('%H:%M')
        store.commit([change('USER#p', 'PREFERENCES', {**DEFAULT_PREFS, 'channels': ['email'], 'quietStart': start, 'quietEnd': end}),
                      change('USER#p', 'CONTACT', {'email': 'test@example.invalid'})])
        event = {'id': 'e', 'school': 's', 'flag': 'red', 'kind': 'threshold-change', 'time': now, 'expiresAt': now + 3600}
        deliver(store, event, email=lambda *a: self.fail('Must not send during quiet hours'), now=now, subject='p')
        self.assertEqual(store.query('USER#p', 'DELIVERY#')[0]['status'], 'suppressed-quiet-hours')
