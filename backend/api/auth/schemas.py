from pydantic import BaseModel, EmailStr, Field

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 256


class SignupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    email: EmailStr
    # Enforced server-side so the rule cannot be bypassed by calling the API
    # directly; the signup form mirrors the same minimum.
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class SigninRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Keep old names as aliases so any existing imports don't break
SignupResponse = AuthResponse
SigninResponse = AuthResponse
