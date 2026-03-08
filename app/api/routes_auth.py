import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.services.audit import write_audit
from app.services.security import create_access_token, decode_access_token, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Simple in-memory rate limiter: {ip: [timestamps]}
_login_attempts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = 5  # max attempts per window


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    attempts = _login_attempts[ip]
    # Prune old entries
    _login_attempts[ip] = [t for t in attempts if now - t < _RATE_LIMIT_WINDOW]
    if len(_login_attempts[ip]) >= _RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    _login_attempts[ip].append(now)


@router.post("/login")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    user = db.execute(select(User).where(User.username == form_data.username)).scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.password_hash):
        write_audit(db, action="auth.login_failed", object_ref=f"user:{form_data.username}", metadata={"ip": client_ip})
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(subject=user.username, role=user.role)
    write_audit(db, action="auth.login_success", object_ref=f"user:{user.id}", user_id=user.id, metadata={"ip": client_ip})
    db.commit()
    logger.info("User '%s' logged in (role: %s)", user.username, user.role)
    return {"access_token": token, "token_type": "bearer", "role": user.role}


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
