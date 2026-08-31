import unittest

from core import tokens
from core.models import get_user_model


def test_user(email='token@hotmail.com', password='123qwe'):
    return get_user_model().objects.create_user(email, password)


class EncodingTests(unittest.TestCase):

    def test_force_bytes_and_back(self):
        self.assertEqual(tokens.force_bytes('pythontr'), b'pythontr')
        self.assertEqual(tokens.force_bytes(b'pythontr'), b'pythontr')
        self.assertEqual(tokens.force_bytes(42), b'42')
        self.assertEqual(tokens.force_str(b'pythontr'), 'pythontr')
        self.assertEqual(tokens.force_str('pythontr'), 'pythontr')
        self.assertEqual(tokens.force_str(42), '42')

    def test_base36_round_trip(self):
        for number in (0, 1, 35, 36, 1234567):
            encoded = tokens.int_to_base36(number)
            self.assertEqual(tokens.base36_to_int(encoded), number)

    def test_int_to_base36_rejects_a_negative_number(self):
        with self.assertRaises(ValueError):
            tokens.int_to_base36(-1)

    def test_base36_to_int_rejects_an_overlong_string(self):
        with self.assertRaises(ValueError):
            tokens.base36_to_int('z' * 14)

    def test_urlsafe_base64_round_trip(self):
        encoded = tokens.urlsafe_base64_encode(b'42')

        self.assertNotIn('=', encoded)
        self.assertEqual(tokens.urlsafe_base64_decode(encoded), b'42')

    def test_urlsafe_base64_decode_rejects_rubbish(self):
        with self.assertRaises(ValueError):
            tokens.urlsafe_base64_decode('a')

    def test_salted_hmac_is_stable_and_salt_dependent(self):
        first = tokens.salted_hmac('salt', 'value', secret='s').hexdigest()
        again = tokens.salted_hmac('salt', 'value', secret='s').hexdigest()
        other = tokens.salted_hmac('pepper', 'value', secret='s').hexdigest()

        self.assertEqual(first, again)
        self.assertNotEqual(first, other)


class PasswordResetTokenTests(unittest.TestCase):

    def setUp(self):
        self.user = test_user()
        self.generator = tokens.default_token_generator

    def test_a_freshly_made_token_checks_out(self):
        token = self.generator.make_token(self.user)

        self.assertTrue(self.generator.check_token(self.user, token))

    def test_a_token_is_refused_without_a_user(self):
        token = self.generator.make_token(self.user)

        self.assertFalse(self.generator.check_token(None, token))

    def test_an_empty_token_is_refused(self):
        self.assertFalse(self.generator.check_token(self.user, ''))

    def test_a_malformed_token_is_refused(self):
        self.assertFalse(self.generator.check_token(self.user, 'nodash'))

    def test_a_token_with_a_bad_timestamp_is_refused(self):
        token = self.generator.make_token(self.user)
        self.assertFalse(
            self.generator.check_token(
                self.user, 'zzzz-' + token.split('-')[1]
            )
        )

    def test_a_tampered_token_is_refused(self):
        timestamp = self.generator.make_token(self.user).split('-')[0]

        self.assertFalse(
            self.generator.check_token(self.user, timestamp + '-deadbeef')
        )

    def test_a_token_is_refused_for_another_user(self):
        token = self.generator.make_token(self.user)
        other = test_user(email='token2@hotmail.com')

        self.assertFalse(self.generator.check_token(other, token))

    def test_a_token_stops_working_once_the_password_changes(self):
        token = self.generator.make_token(self.user)
        self.user.set_password('somethingelse')
        self.user.save()

        self.assertFalse(self.generator.check_token(self.user, token))

    def test_an_expired_token_is_refused(self):
        token = self.generator.make_token(self.user)
        timestamp = tokens.base36_to_int(token.split('-')[0])
        stale = timestamp - (tokens.PASSWORD_RESET_TIMEOUT + 1)
        expired = self.generator._make_token_with_timestamp(
            self.user, stale, self.generator._get_secret()
        )

        self.assertFalse(self.generator.check_token(self.user, expired))
