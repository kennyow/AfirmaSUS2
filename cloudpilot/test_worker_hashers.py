"""Compare the Worker hasher against Django's standard implementation."""
import unittest
from unittest.mock import patch

from django.conf import settings
if not settings.configured:
    settings.configure(SECRET_KEY='test-only', PASSWORD_HASHERS=[
        'cloudpilot.hashers.WorkerPBKDF2PasswordHasher',
    ])
from django.contrib.auth.hashers import PBKDF2PasswordHasher
from cloudpilot.hashers import WorkerPBKDF2PasswordHasher


class WorkerHasherTests(unittest.TestCase):
    def test_matches_standard_including_unicode_and_long_password(self):
        for password, salt, iterations in (
            ('example-test-password', 'fixedTestSalt2026', 1),
            ('ação-coração-🔐', 'salNãoSecreto', 2000),
            ('long' * 100, 'fixedLongSalt2026', 1000),
            ('migration-test-password', 'sourceWorkFactor', 1_500_000),
        ):
            with self.subTest(iterations=iterations, length=len(password)):
                self.assertEqual(
                    WorkerPBKDF2PasswordHasher().encode(password, salt, iterations),
                    PBKDF2PasswordHasher().encode(password, salt, iterations),
                )

    def test_correct_and_incorrect_password_without_stdlib_pbkdf2(self):
        expected = PBKDF2PasswordHasher().encode('test-password', 'saltForTest2026', 2000)
        with patch('hashlib.pbkdf2_hmac', side_effect=AssertionError('unavailable')):
            hasher = WorkerPBKDF2PasswordHasher()
            self.assertTrue(hasher.verify('test-password', expected))
            self.assertFalse(hasher.verify('wrong-password', expected))

    def test_default_work_factor_and_upgrade_policy(self):
        hasher = WorkerPBKDF2PasswordHasher()
        self.assertEqual(hasher.iterations, 1_500_000)
        self.assertFalse(hasher.must_update(hasher.encode('test', hasher.salt())))
        self.assertTrue(hasher.must_update(hasher.encode('test', hasher.salt(), 1000)))

    def test_rejects_invalid_salt(self):
        with self.assertRaises(ValueError):
            WorkerPBKDF2PasswordHasher().encode('test', 'bad$salt')


if __name__ == '__main__':
    unittest.main()
