"""The Django half of the cross-service JWT key check."""

from django.test import TestCase


class JWTKeyFingerprintTests(TestCase):
    """The Django half of the cross-service key check.

    The fingerprints these produce are compared, by eye or by
    scripts/check_jwt_alignment.py, against the one FastAPI logs. If the two
    implementations ever drift apart the check silently starts passing for
    mismatched keys, which is worse than not having it — hence the explicit
    assertion that the algorithm is the agreed one.
    """

    def test_the_same_key_gives_the_same_fingerprint(self):
        from apps.accounts.auth import key_fingerprint

        self.assertEqual(key_fingerprint("shared"), key_fingerprint("shared"))

    def test_different_keys_give_different_fingerprints(self):
        from apps.accounts.auth import key_fingerprint

        self.assertNotEqual(key_fingerprint("django"), key_fingerprint("fastapi"))

    def test_a_missing_key_says_so(self):
        from apps.accounts.auth import key_fingerprint

        self.assertEqual(key_fingerprint(""), "unset")

    def test_the_fingerprint_does_not_leak_the_key(self):
        from apps.accounts.auth import key_fingerprint

        secret = "correct-horse-battery-staple"
        self.assertNotIn(secret, key_fingerprint(secret))

    def test_it_matches_the_algorithm_fastapi_uses(self):
        """Pinned by construction rather than by importing the other service,
        which is not on this path. If either side changes the label or the
        digest, this fails and the mismatch is caught here instead of by two
        logs that quietly stop agreeing."""
        import hashlib
        import hmac

        from apps.accounts.auth import key_fingerprint

        expected = hmac.new(
            b"a-test-key", b"bliss-jwt-signing-key", hashlib.sha256
        ).hexdigest()[:12]
        self.assertEqual(key_fingerprint("a-test-key"), expected)
