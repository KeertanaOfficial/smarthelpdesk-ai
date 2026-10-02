"""
Username/password authentication with opaque bearer tokens.

Deliberately not JWT: tokens are random strings (secrets.token_urlsafe)
stored server-side in the auth_tokens table and looked up on every
request. For a single-instance, SQLite-backed app this is simpler to
reason about than signing/verifying JWTs, needs no secret-key env var
to manage, and tokens can be revoked by just deleting the row.
Tokens expire after TOKEN_TTL_DAYS and the client must log in again.
"""

import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import Header, HTTPException

from app.db.db import SessionLocal
from app.db.models import User, AuthToken

TOKEN_TTL_DAYS = 7


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_token_for_user(db, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        AuthToken(
            token=token,
            user_id=user_id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=TOKEN_TTL_DAYS),
        )
    )
    db.commit()
    return token


def get_current_user(authorization: str = Header(None)) -> User:
    """
    FastAPI dependency. Add `current_user: User = Depends(get_current_user)`
    to any route that should require login. Raises 401 if the
    Authorization header is missing, malformed, or the token is
    unknown/expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
        )

    token = authorization.split(" ", 1)[1].strip()

    db = SessionLocal()
    try:
        auth_token = db.query(AuthToken).filter(AuthToken.token == token).first()

        if not auth_token:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        if auth_token.expires_at and auth_token.expires_at < datetime.utcnow():
            db.delete(auth_token)
            db.commit()
            raise HTTPException(
                status_code=401,
                detail="Session expired, please log in again",
            )

        user = db.query(User).filter(User.id == auth_token.user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user
    finally:
        db.close()
