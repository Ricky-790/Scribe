from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.api.auth.security import decode_jwt

_bearer = HTTPBearer(auto_error=False)


class AuthenticatedUser:
    """Parsed, validated token payload attached to a request."""

    def __init__(self, user_id: UUID, email: str) -> None:
        self.user_id = user_id
        self.email = email


def _authenticated_user_from_token(token: str) -> AuthenticatedUser:
    """Validate a Bearer token and return its payload.

    Raises HTTP 401 for expired, invalid, or malformed tokens.
    """
    try:
        payload = decode_jwt(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return AuthenticatedUser(
            user_id=UUID(payload["id"]),
            email=payload["email"],
        )
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    """
    FastAPI dependency that validates the Bearer JWT and returns the
    parsed token payload as an AuthenticatedUser.

    Raises HTTP 401 for missing, malformed, or expired tokens.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _authenticated_user_from_token(credentials.credentials)


async def get_redis_client(request: Request):
    """Return the shared Redis client held on app state by the lifespan hook."""
    return request.app.state.redis_client
