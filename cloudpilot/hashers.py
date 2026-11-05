"""Django-compatible PBKDF2 using the Pyodide-supported native crypto package."""
import base64

from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from django.contrib.auth.hashers import PBKDF2PasswordHasher
from django.utils.encoding import force_bytes


class WorkerPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    # Match the source account's work factor; do not downgrade migrated passwords.
    iterations = 1_500_000

    def encode(self, password, salt, iterations=None):
        self._check_encode_args(password, salt)
        iterations = iterations or self.iterations
        derived = PBKDF2(
            force_bytes(password), force_bytes(salt), dkLen=32,
            count=iterations, hmac_hash_module=SHA256,
        )
        encoded = base64.b64encode(derived).decode('ascii').strip()
        return '%s$%d$%s$%s' % (self.algorithm, iterations, salt, encoded)
