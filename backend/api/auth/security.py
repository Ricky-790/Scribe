import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()

JWT_SECRET = os.getenv("JWT_SECRET", "changeme")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


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
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """
    Decode and validate a JWT.
    Raises jwt.PyJWTError on invalid / expired tokens — let callers handle it.
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
