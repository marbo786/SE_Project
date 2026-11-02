"""Passwords and opaque, revocable sessions. Raw tokens are never persisted."""
from datetime import datetime, timedelta
import hashlib
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
import bcrypt
from fastapi import Response
from .config import get_settings
from ..models.session import AuthSession

_hasher = PasswordHasher()

def verify_password(password: str, hashed: str) -> bool:
    try:
        if hashed.startswith("$argon2"):
            return _hasher.verify(hashed, password)
        if hashed.startswith(("$2a$", "$2b$", "$2y$")):
            # Existing bcrypt accounts used the algorithm's 72-byte limit.
            return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("ascii"))
        return False
    except (VerificationError, InvalidHashError, ValueError, TypeError):
        return False

def get_password_hash(password: str) -> str:
    return _hasher.hash(password)

def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def create_session(db, user, response: Response):
    settings = get_settings()
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    lifetime = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    session = AuthSession(user_id=user.id, token_hash=token_digest(token), csrf_hash=token_digest(csrf),
        expires_at=datetime.utcnow() + timedelta(seconds=lifetime))
    db.add(session)
    db.commit()
    for name, value, httponly in [("srs_session", token, True), ("srs_csrf", csrf, False)]:
        response.set_cookie(name, value, max_age=lifetime, httponly=httponly,
            secure=settings.COOKIE_SECURE, samesite="lax", path="/")
    return {"access_token": token, "token_type": "bearer", "user": user}
