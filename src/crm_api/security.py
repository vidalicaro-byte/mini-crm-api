"""Password hashing (Argon2) and access tokens (JWT signed with HMAC-SHA256)."""

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from crm_api.config import Settings
from crm_api.models import User

_password_hash = PasswordHash.recommended()

# Verified when the e-mail is unknown, so a wrong e-mail takes as long as a wrong password and
# response times don't reveal which e-mails have accounts.
_DUMMY_HASH = _password_hash.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False
    return _password_hash.verify(password, password_hash)


def create_access_token(user: User, settings: Settings, now: datetime | None = None) -> str:
    issued_at = now or datetime.now(UTC)
    payload = {
        "sub": user.id,
        "role": user.role.value,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), settings.jwt_algorithm)


def read_token_subject(token: str, settings: Settings) -> str | None:
    """The user id inside a valid token, or None if it is malformed, tampered with or expired."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            # Pinning the algorithm blocks "alg: none" and algorithm-confusion attacks.
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.InvalidTokenError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None
