import hashlib
import base64
import jwt
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from django.conf import settings
from django.utils import timezone as django_timezone
from .models import RefreshToken

ph = PasswordHasher()


def generate_jti():
    return str(uuid.uuid4())


def get_code_challenge(code_verifier: str) -> str:
    """
    Generate S256 code_challenge from code_verifier.
    code_challenge = base64url(sha256(code_verifier))
    """
    sha256_hash = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(sha256_hash).decode("ascii").rstrip("=")


def validate_pkce(
    code_verifier: str, code_challenge: str, method: str = "S256"
) -> bool:
    if method != "S256":
        return False  # Only S256 is supported as per REL-18
    return secrets.compare_digest(get_code_challenge(code_verifier), code_challenge)


def generate_jwt(user, scopes, relationship_id=None):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "jti": generate_jti(),
        "scope": scopes,
        "relationship_id": str(relationship_id) if relationship_id else None,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token, payload


def decode_jwt(token):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def create_refresh_token_record(user, family_id=None):
    token_plaintext = secrets.token_urlsafe(64)
    hashed_token = ph.hash(token_plaintext)

    expires_at = django_timezone.now() + timedelta(days=30)

    rt = RefreshToken.objects.create(
        user=user,
        hashed_token=hashed_token,
        family_id=family_id or uuid.uuid4(),
        expires_at=expires_at,
    )

    return rt, token_plaintext


def rotate_refresh_token(old_token_record, plaintext_token):
    """
    On use: invalidate current token, issue new access + refresh pair
    On reuse detected: invalidate entire token family
    """
    # 1. Verify plaintext against stored hash
    try:
        ph.verify(old_token_record.hashed_token, plaintext_token)
    except Exception:
        # If hash verification fails, it's an invalid token usage attempt
        # But we should only trigger family revocation if the token record was already used
        raise ValueError("Invalid refresh token")

    # 2. Check for reuse
    if old_token_record.used_at:
        # REUSE DETECTED: Invalidate entire family
        RefreshToken.objects.filter(family_id=old_token_record.family_id).delete()
        raise ValueError("Refresh token reuse detected. Family revoked.")

    # 3. Check for expiry
    if django_timezone.now() > old_token_record.expires_at:
        raise ValueError("Refresh token expired")

    # 4. Mark as used
    old_token_record.used_at = django_timezone.now()
    old_token_record.save()

    # 5. Issue new token in same family
    return create_refresh_token_record(
        old_token_record.user, family_id=old_token_record.family_id
    )


def revoke_family(family_id):
    RefreshToken.objects.filter(family_id=family_id).delete()
