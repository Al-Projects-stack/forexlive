import re
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.services.auth import register_user, login_user, create_access_token

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$')
PASSWORD_RE = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$')


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=80)

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address")
        return v

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if not PASSWORD_RE.match(v):
            raise ValueError(
                "Password must be at least 8 characters with uppercase, lowercase, and a number"
            )
        return v

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        return v


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("10/minute")
async def register(request: Request, body: RegisterRequest):
    try:
        user = register_user(body.email, body.password, body.full_name)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    token = create_access_token(user["id"], user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user["id"], "email": user["email"], "full_name": user["full_name"]},
    }


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
async def login(request: Request, body: LoginRequest):
    user = login_user(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user["id"], "email": user["email"], "full_name": user["full_name"]},
    }


@router.get("/me")
async def me(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    from app.services.auth import decode_token
    payload = decode_token(auth_header[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    return {"id": payload["sub"], "email": payload["email"]}
