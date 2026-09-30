import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from uuid import UUID

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash

load_dotenv()

_password_hash = PasswordHash.recommended()

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


class MissingJWTSecretError(RuntimeError):
    """Raised when JWT_SECRET is absent, so tokens can never be forged."""


@lru_cache(maxsize=1)
def get_jwt_secret() -> str:
    """
    Return the JWT signing secret.

    Resolved lazily on first use rather than at import time: this module is
    imported by ``main.py`` before ``load_dotenv()`` runs there, so an
    import-time read would miss a secret supplied via ``.env``.

    Fails closed — there is no default, so a misconfigured deployment raises
    instead of silently signing tokens with a publicly known value.
    """
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise MissingJWTSecretError(
            "JWT_SECRET is not set. Generate one with "
            "`python -c \"import secrets; print(secrets.token_urlsafe(48))\"` "
            "and add it to your .env file."
        )
    return secret


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


def encode_jwt(user_id: UUID, email: str) -> str:
    payload = {
        "id": str(user_id),
        "email": email,
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """
    Decode and validate a JWT.
    Raises jwt.PyJWTError on invalid / expired tokens — let callers handle it.
    """
    return jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
