"""
auth.py — JWT Authentication for the Algo Trading API

Credentials (hardcoded for Step 7 demo):
  username : Admin
  password : admin@123

Provides:
  - create_access_token()   : Generate a signed JWT
  - verify_token()          : Decode and validate a JWT
  - authenticate_user()     : Validate username + password
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

# ── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY: str = os.getenv("JWT_SECRET", "algo-trading-secret-key-2024-change-in-prod")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

# ── Password hashing context ──────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Hardcoded user store (Step 7 demo — replace with DB in production) ────────
USERS_DB: dict = {
    "Admin": {
        "username": "Admin",
        # pre-hashed version of "admin@123"
        "hashed_password": pwd_context.hash("admin@123"),
        "role": "admin",
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain-text password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Validate username and password against the user store.

    Returns:
        User dict on success, None on failure.
    """
    user = USERS_DB.get(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user

def register_user(username: str, password: str) -> bool:
    """Register a new user to the in-memory store."""
    if username in USERS_DB:
        return False
    USERS_DB[username] = {
        "username": username,
        "hashed_password": pwd_context.hash(password),
        "role": "user",
    }
    return True


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a signed JWT access token.

    Args:
        data:          Payload to encode (must include 'sub' key).
        expires_delta: Token lifetime (defaults to ACCESS_TOKEN_EXPIRE_MINUTES).

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.

    Returns:
        Decoded payload dict if valid, None if expired or invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
