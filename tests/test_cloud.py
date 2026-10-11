import json
import os
import time
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

from backend.functions import air_engine
from cloud import api, providers
from cloud.contracts import Problem, school, DEFAULT_PREFS
from cloud.store import MemoryStore, DynamoStore, change, Conflict
from cloud.policy import plan, sensor_quality
from cloud.pipeline import ingest, history, relay
from cloud.notifications import deliver
from cloud.sensors import ingest_sensor
from cloud.forecast import evaluate
from scripts.bootstrap_school import bootstrap


def fixture_air(now, pm=45):
    station = {'id': 'cams', 'name': 'Regional model', 'source': 'Open-Meteo / CAMS', 'kind': 'model',
               'lat': 28.6, 'lon': 77.2, 'pm25': pm, 'pm10': 70, 'observedAt': air_engine.iso(now)}
    result = air_engine.estimate({'lat': 28.6, 'lon': 77.2}, [station])
    result.update(source='Open-Meteo / CAMS', mode='live', forecast=[], forecastSource='CAMS',
                  providers=[], indices=[], fetchedAt=air_engine.iso(now), retentionApproved=True, stale=False)
    return result


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.store, self.readings = MemoryStore(), MemoryStore()
        self.now = time.time()
        self.school = school({'id': 'a', 'name': 'School A', 'lat': 28.6, 'lon': 77.2})
        bootstrap(self.store, self.school, 'admin')
        bootstrap(self.store, school({'id': 'b', 'name': 'School B', 'lat': 19, 'lon': 72}), 'other-admin')
        for sub, role, cid in [('parent', 'parent', None), ('teacher', 'teacher', 'c1'), ('staff', 'staff', None), ('other-parent', 'parent', None)]:
            self.store.commit([change('SCHOOL#a', 'MEMBER#' + sub, {'sub': sub, 'school': 'a', 'role': role, 'class_id': cid, 'active': True}),
                               change('USER#' + sub, 'SCHOOL#a', {'school': 'a'})])
        self.store.commit([change('SCHOOL#a', 'CLASS#c1', {'id': 'c1', 'label': 'Class 1'}),
                           change('SCHOOL#a', 'CHILD#kid', {'id': 'kid', 'alias': 'Alias A', 'class_id': 'c1', 'age_group': '5-8',
                                                         'caution': True, 'guardians': ['parent']})])
        self.air = fixture_air(self.now)
        ingest(self.store, self.readings, self.school, self.air, self.now)

    def call(self, action, data=None, sub='admin', method='POST', sid='a', contact=None):
        return api.application(self.store, self.readings, method, '/v1/schools/' + sid + '/' + action, data or {}, {}, sub, contact)

    def test_cross_school_and_role_forgery_denied(self):
        with self.assertRaises(Problem) as error:
            self.call('workspace', sub='parent', method='GET', sid='b')
        self.assertEqual(error.exception.status, 403)
        with self.assertRaises(Problem):
            self.call('announce', {'role': 'admin', 'note': 'Forged', 'requestId': 'x'}, sub='parent')

    def test_staff_has_no_child_data_and_teacher_has_no_parent_details(self):
        self.assertEqual(self.call('workspace', sub='staff', method='GET')['children'], [])
        child = self.call('workspace', sub='teacher', method='GET')['children'][0]
        self.assertEqual(set(child), {'id', 'alias', 'extraCaution'})
        self.assertEqual(self.call('workspace', sub='other-parent', method='GET')['children'], [])

    def test_wrong_guardian_cannot_write(self):
        with self.assertRaises(Problem):
            self.call('checkin', {'childId': 'kid', 'signal': True}, sub='other-parent')

    def test_revocation_takes_effect_without_new_token(self):
        self.call('revoke', {'sub': 'parent'})
        with self.assertRaises(Problem):
            self.call('workspace', sub='parent', method='GET')
        result = api.application(self.store, self.readings, 'GET', '/v1/session', {}, {}, 'parent')
        self.assertEqual(result['memberships'], [])

    def test_publish_ack_review_idempotency(self):
        event = self.call('announce', {'note': 'Review indoor PE.', 'requestId': 'notice-1'})['event']
        repeat = self.call('announce', {'note': 'Review indoor PE.', 'requestId': 'notice-1'})['event']
        self.assertEqual(event, repeat)
        self.call('acknowledge', {'eventId': event['id'], 'checks': [True] * 3, 'minutesMoved': 30}, sub='teacher')
        for _ in range(2):
            self.call('review', {'eventId': event['id']}, sub='parent')
        self.assertEqual(len(self.call('workspace', method='GET')['receipts']), 2)
        self.call('announce', {'note': 'Updated plan.', 'requestId': 'notice-2'})
        with self.assertRaises(Problem):
            self.call('review', {'eventId': event['id']}, sub='parent')

    def test_incomplete_checklist_rejected(self):
        self.call('announce', {'note': 'Review PE.', 'requestId': 'notice'})
        for checks in ([True, False, True], [1, 1, 1]):
            with self.assertRaises(Problem):
                self.call('acknowledge', {'eventId': 'notice', 'checks': checks, 'minutesMoved': 20}, sub='teacher')

    def test_invitation_email_binding_single_use(self):
        invitation = self.call('invite', {'email': 'invited@example.com', 'role': 'parent', 'children': ['kid']})
        with self.assertRaises(Problem):
            api.application(self.store, self.readings, 'POST', '/v1/enroll', {'token': invitation['token']}, {}, 'new', 'wrong@example.com')
        api.application(self.store, self.readings, 'POST', '/v1/enroll', {'token': invitation['token']}, {}, 'new', 'invited@example.com')
        self.assertIn('new', self.store.get('SCHOOL#a', 'CHILD#kid')['guardians'])
        with self.assertRaises(Problem):
            api.application(self.store, self.readings, 'POST', '/v1/enroll', {'token': invitation['token']}, {}, 'new2', 'invited@example.com')

    def test_unverified_email_preferences_are_atomic(self):
        with self.assertRaises(Problem):
            self.call('preferences', {**DEFAULT_PREFS, 'channels': ['email']}, sub='parent')
        self.assertIsNone(self.store.get('USER#parent', 'PREFERENCES'))

    def test_push_endpoint_rejects_internal_and_untrusted_hosts(self):
        for endpoint in ['https://127.0.0.1/push', 'https://fcm.googleapis.com.attacker.test/push', 'http://fcm.googleapis.com/push']:
            with self.assertRaises(Problem):
                api.validate_push({'endpoint': endpoint})

    def test_ingestion_deduplicates_and_ignores_old_observation(self):
        result = ingest(self.store, self.readings, self.school, self.air, self.now + 10)
        self.assertIsNone(result['eventId'])
        rows = history(self.readings, 'a', 7, self.now + 10)['readings']
        self.assertEqual(len(rows), 1)
        result = ingest(self.store, self.readings, self.school, fixture_air(self.now - 3600), self.now + 20)
        self.assertEqual(result['status'], 'ignored-older-observation')

    def test_stale_input_never_green(self):
        stale = fixture_air(self.now - 8000, 5)
        self.assertEqual(plan(stale, self.school, now=self.now)['flag'], 'unknown')
        failed = dict(self.air, observedAt=None, pm25=None, stale=True)
        ingest(self.store, self.readings, self.school, failed, self.now + 20)
        self.assertEqual(self.call('workspace', method='GET')['planning']['flag'], 'unknown')

    def test_expired_rows_are_not_returned_before_ttl_deletion(self):
        self.store.commit([change('private', 'expired', {'secret': 'gone'}, expires=self.now - 1)])
        self.assertIsNone(self.store.get('private', 'expired'))
        self.assertEqual(self.store.query('private'), [])

    def test_exposure_cap_and_retry(self):
        value = {'childId': 'kid', 'minutes': 720, 'concentration': 10, 'context': 'outdoor', 'requestId': 'x'}
        self.call('exposure', value, sub='parent'); self.call('exposure', value, sub='parent')
        self.call('exposure', dict(value, requestId='y'), sub='parent')
        with self.assertRaises(Problem):
            self.call('exposure', dict(value, requestId='z'), sub='parent')

    def test_unlink_removes_access_and_private_records(self):
        self.call('checkin', {'childId': 'kid', 'signal': True}, sub='parent')
        self.call('membership', sub='parent', method='DELETE')
        self.assertEqual(self.store.query('USER#parent', 'CHECKIN#a#'), [])
        self.assertEqual(self.store.get('SCHOOL#a', 'CHILD#kid')['guardians'], [])
        with self.assertRaises(Problem):
            self.call('workspace', sub='parent', method='GET')

    def test_delivery_retry_skips_successful_device_and_caps_per_channel(self):
        self.store.commit([change('USER#parent', 'PREFERENCES', {**DEFAULT_PREFS, 'channels': ['push'], 'quietStart': '00:00', 'quietEnd': '00:00'}),
            change('USER#parent', 'PUSH#one', {'subscription': {'endpoint': 'one'}}),
            change('USER#parent', 'PUSH#two', {'subscription': {'endpoint': 'two'}})])
        event = self.call('announce', {'note': 'School plan.', 'requestId': 'delivery'})['event']
        sent = []
        def flaky(sub, message):
            if sub['endpoint'] == 'two':
                raise RuntimeError('temporary')
            sent.append(sub['endpoint']); return 'accepted-by-push-service'
        with self.assertRaises(RuntimeError):
            deliver(self.store, event, push=flaky, now=self.now, subject='parent')
        def success(sub, message):
            sent.append(sub['endpoint']); return 'accepted-by-push-service'
        deliver(self.store, event, push=success, now=self.now + 1, subject='parent')
        self.assertEqual(sent, ['one', 'two'])
        caps = self.store.query('USER#parent', 'CAP#')
        self.assertEqual(caps[0]['count'], 1)

    def test_unsubscribed_or_revoked_user_receives_nothing(self):
        event = self.call('announce', {'note': 'Plan.', 'requestId': 'revoked-delivery'})['event']
        self.call('revoke', {'sub': 'parent'})
        deliver(self.store, event, push=lambda *args: self.fail('Must not send'), now=self.now, subject='parent')
        self.assertEqual(self.store.query('USER#parent', 'DELIVERY#'), [])

    def test_sensor_spoofed_school_and_old_buffer(self):
        self.store.commit([change('DEVICES', 'sensor1', {'id': 'sensor1', 'school': 'a', 'active': True, 'location': 'gate', 'room_id': 'gate'})])
        data = {'deviceId': 'sensor1', 'school': 'b', 'observedAt': air_engine.iso(self.now), 'pm25': 40, 'humidity': 50, 'sampleCount': 60, 'sequence': 1}
        ingest_sensor(self.store, self.readings, data, self.now)
        self.assertEqual(self.store.get('SCHOOL#a', 'SENSOR#sensor1')['school'], 'a')
        self.assertIsNone(self.store.get('SCHOOL#b', 'SENSOR#sensor1'))
        old = dict(data, observedAt=air_engine.iso(self.now - 1800), sequence=0)
        result = ingest_sensor(self.store, self.readings, old, self.now)
        self.assertEqual(result['status'], 'duplicate-or-buffered')
        self.assertEqual(self.store.get('SCHOOL#a', 'SENSOR#sensor1')['sequence'], 1)

    def test_high_humidity_requires_review(self):
        result = sensor_quality({'observedAt': air_engine.iso(self.now), 'pm25': 10, 'humidity': 95, 'sampleCount': 60}, now=self.now)
        self.assertEqual(result['quality'], 'review')

    def test_cpcb_unknown_units_never_become_concentrations(self):
        data = {'records': [{'pollutant_id': 'PM2.5', 'pollutant_avg': 99, 'pollutant_unit': 'NA'}]}
        with patch.dict(os.environ, {'CPCB_RESOURCE_ID': '3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69'}), patch.object(air_engine, 'request_json', return_value=data):
            self.assertEqual(providers.cpcb({**self.school, 'cpcb_city': 'Delhi'}, 'fake')['stations'], [])

    def test_provider_failures_return_unavailable_not_fixtures(self):
        with patch.object(air_engine, 'openmeteo', side_effect=RuntimeError('failure')):
            result = providers.fetch(self.school, {}, self.now)
        self.assertIsNone(result['pm25']); self.assertEqual(result['mode'], 'live')
        self.assertTrue(result['stale'])

    def test_forecast_evaluation_excludes_modeled_targets(self):
        run = {'source': 'model', 'retrievedAt': air_engine.iso(self.now), 'points': [{'time': air_engine.iso(self.now + 3600), 'pm25': 20}]}
        actual = {'observedAt': air_engine.iso(self.now + 3600), 'pm25': 10, 'kind': 'model'}
        self.assertEqual(evaluate([run], [actual]), [])
        result = evaluate([run], [dict(actual, kind='station')])
        self.assertEqual(result[0]['mae'], 10)


class DynamoIntegrationTests(unittest.TestCase):
    def setUp(self):
        from moto import mock_aws
        import boto3
        self.mock = mock_aws(); self.mock.start()
        self.env = patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'ap-south-1', 'APP_TABLE': 'application', 'READINGS_TABLE': 'readings'})
        self.env.start()
        client = boto3.client('dynamodb', region_name='ap-south-1')
        for name in ('application', 'readings'):
            client.create_table(TableName=name, BillingMode='PAY_PER_REQUEST',
                AttributeDefinitions=[{'AttributeName': k, 'AttributeType': 'S'} for k in ('pk', 'sk')],
                KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}])
        self.store = DynamoStore('application')

    def tearDown(self):
        self.env.stop(); self.mock.stop()

    def test_transaction_failure_rolls_back_other_writes(self):
        self.store.commit([change('p', 'a', {'value': 1})])
        with self.assertRaises(Conflict):
            self.store.commit([change('p', 'a', {'value': 2}), change('p', 'b', {'value': 3})])
        self.assertEqual(self.store.get('p', 'a')['value'], 1)
        self.assertIsNone(self.store.get('p', 'b'))

    def test_float_json_round_trip_and_prefix_query(self):
        self.store.commit([change('p', 'X#1', {'pm25': 23.5}), change('p', 'Y#1', {'pm25': 99.0})])
        self.assertEqual(self.store.query('p', 'X#')[0]['pm25'], 23.5)

    def test_dynamo_expiry_and_delete(self):
        self.store.commit([change('p', 'expired', {'value': 1}, expires=time.time() - 1), change('p', 'live', {'value': 2})])
        self.assertEqual(len(self.store.query('p')), 1)
        row = self.store.get('p', 'live')
        self.store.commit([change('p', 'live', None, row)])
        self.assertIsNone(self.store.get('p', 'live'))

    def test_ingestion_to_outbox_to_sqs_recipient_job(self):
        import boto3
        now = time.time()
        config = school({'id': 'a', 'name': 'School A', 'lat': 28.6, 'lon': 77.2})
        bootstrap(self.store, config, 'admin')
        ingest(self.store, DynamoStore('readings'), config, fixture_air(now), now)
        queue = boto3.client('sqs').create_queue(QueueName='delivery')['QueueUrl']
        with patch.dict(os.environ, {'DELIVERY_QUEUE': queue}):
            result = relay({}, None)
        self.assertEqual(result['queued'], 1)
        self.assertEqual(self.store.query('OUTBOX'), [])
        messages = boto3.client('sqs').receive_message(QueueUrl=queue)['Messages']
        self.assertEqual(json.loads(messages[0]['Body'])['sub'], 'admin')


if __name__ == '__main__':
    unittest.main()
