from pwdlib import PasswordHash
import secrets
from .config import Settings
from datetime import datetime, timedelta, timezone
import jwt

settings = Settings() # pyright: ignore[reportCallIssue]

passwordhash = PasswordHash.recommended()

def hash_password(password: str):
    return passwordhash.hash(password)

def verify_password(new_password, hashed_password):
    return passwordhash.verify(new_password, hashed_password)

def generate_4_digit_code():
    return f"{secrets.randbelow(10_000):04d}"

def create_access_token(data: dict, expire_delta: timedelta | None = None) -> str:
    to_encode = data.copy()

    if expire_delta:
        expire = datetime.now(timezone.utc) + expire_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp":expire})

    access_token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return access_token

def create_refresh_token(data: dict, expire_delta: timedelta | None = None) -> str:
    to_encode = data.copy()

    if expire_delta:
        expire = datetime.now(timezone.utc) + expire_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=365)

    to_encode.update({"exp": expire})

    refresh_token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return refresh_token

def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)

def create_reset_token(email: str) -> str:
    expire = datetime.now() + timedelta(minutes=15)
    to_encode = {"sub": email, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)