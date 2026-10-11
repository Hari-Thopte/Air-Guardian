import unittest
from unittest.mock import Mock
from cloud.account import account
from cloud.contracts import Problem
from cloud.store import MemoryStore, change
from scripts.delete_account import erase_application


class AccountTests(unittest.TestCase):
    def test_staged_school_has_no_access_and_bootstrap_cannot_overwrite_admin(self):
        from scripts.bootstrap_school import stage, bootstrap
        from cloud.contracts import school
        store = MemoryStore()
        config = school({'id': 's', 'name': 'Pilot', 'lat': 19, 'lon': 72})
        self.assertTrue(stage(store, config))
        self.assertEqual(store.query('SCHOOL#s', 'MEMBER#'), [])
        bootstrap(store, config, 'verified-admin')
        self.assertFalse(stage(store, config))
        with self.assertRaises(ValueError):
            bootstrap(store, config, 'other-admin')
        self.assertIsNone(store.get('SCHOOL#s', 'MEMBER#other-admin'))

    def setUp(self):
        self.store = MemoryStore()
        self.client = Mock()
        self.client.get_user.return_value = {'UserAttributes': [{'Name': 'sub', 'Value': 'adult'}]}

    def call(self, path, data=None, subject='adult'):
        return account(self.store, subject, 'private-token', 'POST', path, data or {}, self.client)

    def test_cannot_change_another_identity_or_mark_phone_verified(self):
        with self.assertRaises(Problem):
            self.call('/v1/account/phone', {'phone': '+919876543210'}, subject='other')
        self.client.update_user_attributes.assert_not_called()
        self.call('/v1/account/phone', {'phone': '+919876543210', 'phone_number_verified': True})
        self.assertEqual(self.client.update_user_attributes.call_args.kwargs['UserAttributes'],
                         [{'Name': 'phone_number', 'Value': '+919876543210'}])

    def test_invalid_phone_and_code_never_reach_cognito(self):
        with self.assertRaises(Problem):
            self.call('/v1/account/phone', {'phone': '9876543210'})
        with self.assertRaises(Problem):
            self.call('/v1/account/phone/verify', {'code': 'oops'})
        self.client.update_user_attributes.assert_not_called()
        self.client.verify_user_attribute.assert_not_called()

    def test_changing_phone_clears_old_delivery_contact(self):
        self.store.commit([change('USER#adult', 'CONTACT', {'phone': '+919111111111', 'email': 'adult@example.com'})])
        self.call('/v1/account/phone', {'phone': '+919876543210'})
        self.assertNotIn('phone', self.store.get('USER#adult', 'CONTACT'))
        self.assertEqual(self.store.get('USER#adult', 'CONTACT')['email'], 'adult@example.com')

    def test_cognito_verification_error_is_safe_and_specific(self):
        from botocore.exceptions import ClientError
        self.client.verify_user_attribute.side_effect = ClientError(
            {'Error': {'Code': 'CodeMismatchException', 'Message': 'private-provider-detail'}}, 'VerifyUserAttribute')
        with self.assertRaises(Problem) as error:
            self.call('/v1/account/phone/verify', {'code': '123456'})
        self.assertEqual(error.exception.status, 400)
        self.assertNotIn('private-provider-detail', str(error.exception))

    def test_verification_rate_limit_and_kid_restriction(self):
        for _ in range(3):
            self.call('/v1/account/phone/resend')
        with self.assertRaises(Problem) as error:
            self.call('/v1/account/phone/resend')
        self.assertEqual(error.exception.status, 429)
        self.store.commit([change('USER#adult', 'SCHOOL#s', {'school': 's'}),
                           change('SCHOOL#s', 'MEMBER#adult', {'active': True, 'role': 'kid'})])
        with self.assertRaises(Problem):
            self.call('/v1/account/phone', {'phone': '+919876543210'})

    def test_erasure_is_restartable_and_preserves_other_guardian(self):
        self.store.commit([change('SCHOOL#s', 'MEMBER#adult', {'active': True}),
                           change('SCHOOL#s', 'CHILD#one', {'guardians': ['adult']}),
                           change('SCHOOL#s', 'CHILD#shared', {'guardians': ['adult', 'other']}),
                           change('USER#adult', 'CONTACT', {'email': 'private@example.com'}),
                           change('USER#other', 'CONTACT', {'email': 'other@example.com'})])
        erase_application(self.store, 'adult', ['s'])
        erase_application(self.store, 'adult', ['s'])
        self.assertIsNone(self.store.get('SCHOOL#s', 'CHILD#one'))
        self.assertEqual(self.store.get('SCHOOL#s', 'CHILD#shared')['guardians'], ['other'])
        self.assertEqual(self.store.query('USER#adult'), [])
        self.assertIsNotNone(self.store.get('USER#other', 'CONTACT'))
