from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth.schemas import AuthResponse, SigninRequest, SignupRequest
from backend.api.auth.security import encode_jwt, hash_password, verify_password
from backend.db.services.user_service import users_service
from backend.db.session import get_session

router = APIRouter()


@router.post(
    "/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def signup(
    payload: SignupRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    """
    Register a new user.
    - 409 if the email is already taken.
    - Returns a signed JWT on success.
    """
    if await users_service.email_exists(session, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = await users_service.create_user(
        session,
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )

    token = encode_jwt(user.id, user.email)
    return AuthResponse(access_token=token)


@router.post("/signin", response_model=AuthResponse)
async def signin(
    payload: SigninRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    """
    Authenticate an existing user.
    - 401 if the email is not found or the password is wrong.
    - Returns a signed JWT on success.
    """
    user = await users_service.get_user_by_email(session, payload.email)

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = encode_jwt(user.id, user.email)
    return AuthResponse(access_token=token)
