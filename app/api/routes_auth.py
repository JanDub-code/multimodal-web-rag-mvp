import logging
import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import RefreshToken, User
from app.db.session import get_db
from app.services.audit import write_audit
from app.services.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    get_refresh_token_expiry,
    hash_token,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Simple in-memory rate limiter: {ip: [timestamps]}
_login_attempts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = 5  # max attempts per window


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=32, max_length=2048)


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    attempts = _login_attempts[ip]
    # Prune old entries
    _login_attempts[ip] = [t for t in attempts if now - t < _RATE_LIMIT_WINDOW]
    if len(_login_attempts[ip]) >= _RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    _login_attempts[ip].append(now)


def _issue_refresh_token(db: Session, user_id: int) -> str:
    plain_token = create_refresh_token()
    token_row = RefreshToken(
        user_id=user_id,
        token_hash=hash_token(plain_token),
        expires_ts=get_refresh_token_expiry(),
    )
    db.add(token_row)
    db.flush()
    return plain_token


def _get_active_refresh_token(db: Session, token_hash: str) -> RefreshToken | None:
    row = db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).scalar_one_or_none()
    if not row:
        return None
    now = datetime.now(timezone.utc)
    expires_ts = row.expires_ts
    if expires_ts.tzinfo is None:
        expires_ts = expires_ts.replace(tzinfo=timezone.utc)
    if row.revoked_ts is not None or expires_ts <= now:
        return None
    return row


@router.post("/login")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    user = db.execute(select(User).where(User.username == form_data.username)).scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.password_hash):
        write_audit(db, action="auth.login_failed", object_ref=f"user:{form_data.username}", metadata={"ip": client_ip})
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(subject=user.username, role=user.role)
    refresh_token = _issue_refresh_token(db, user_id=user.id)
    write_audit(db, action="auth.login_success", object_ref=f"user:{user.id}", user_id=user.id, metadata={"ip": client_ip})
    db.commit()
    logger.info("User '%s' logged in (role: %s)", user.username, user.role)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role,
    }


@router.post("/refresh")
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    old_hash = hash_token(payload.refresh_token)
    token_row = _get_active_refresh_token(db, old_hash)
    if not token_row:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.get(User, token_row.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_refresh = _issue_refresh_token(db, user_id=user.id)
    now = datetime.now(timezone.utc)
    token_row.revoked_ts = now
    token_row.replaced_by_token_hash = hash_token(new_refresh)

    access_token = create_access_token(subject=user.username, role=user.role)
    write_audit(
        db,
        action="auth.refresh_success",
        object_ref=f"user:{user.id}",
        user_id=user.id,
        metadata={"refresh_rotated": True},
    )
    db.commit()
    return {
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "role": user.role,
    }


@router.post("/logout")
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_hash = hash_token(payload.refresh_token)
    token_row = db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).scalar_one_or_none()

    revoked = False
    user_id = None
    if token_row and token_row.revoked_ts is None:
        token_row.revoked_ts = datetime.now(timezone.utc)
        revoked = True
    if token_row:
        user_id = token_row.user_id

    write_audit(
        db,
        action="auth.logout",
        object_ref=f"user:{user_id}" if user_id is not None else "user:unknown",
        user_id=user_id,
        metadata={"refresh_revoked": revoked},
    )
    db.commit()
    return {"status": "ok"}


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_roles(*roles: str):
    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return _checker
