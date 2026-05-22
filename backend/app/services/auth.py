import os
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional

SECRET_KEY = os.environ.get("JWT_SECRET", "forexlive-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# In-memory user store — swap for DB in production
_users: dict[str, dict] = {}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def register_user(email: str, password: str, full_name: str) -> dict:
    email = email.lower().strip()
    if email in _users:
        raise ValueError("Email already registered")
    user = {
        "id": str(len(_users) + 1),
        "email": email,
        "full_name": full_name,
        "password_hash": hash_password(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _users[email] = user
    return user


def login_user(email: str, password: str) -> Optional[dict]:
    email = email.lower().strip()
    user = _users.get(email)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def get_user_by_email(email: str) -> Optional[dict]:
    return _users.get(email.lower().strip())
