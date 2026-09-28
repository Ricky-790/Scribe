from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.api.auth.security import decode_jwt

_bearer = HTTPBearer()


class AuthenticatedUser:
    """Parsed, validated token payload attached to a request."""

    def __init__(self, user_id: UUID, email: str) -> None:
        self.user_id = user_id
        self.email = email


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> AuthenticatedUser:
    """
    FastAPI dependency that validates the Bearer JWT and returns the
    parsed token payload as an AuthenticatedUser.

    Raises HTTP 401 for missing, malformed, or expired tokens.
    """
    token = credentials.credentials
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


async def get_current_user_ws(ws: WebSocket):
    token = ws.query_params.get("token")
    if token is None:
        raise HTTPException(status_code=401)

    payload = decode_jwt(token)
    return AuthenticatedUser(
        user_id=UUID(payload["id"]),
        email=payload["email"],
    )


async def get_redis_client(websocket: WebSocket):
    return websocket.app.state.redis_client
