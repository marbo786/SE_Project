from datetime import datetime, timedelta
import secrets
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.security import verify_password, get_password_hash, create_session, token_digest
from ..core.deps import get_current_user, validate_origin
from ..core.limits import enforce_limit
from ..core.mail import deliver_challenge
from ..models.user import User
from ..models.session import AuthSession, AuthChallenge
from ..schemas.user import UserCreate, UserLogin, Token, UserOut, RecoveryRequest, ResetPassword, VerifyEmail

router = APIRouter(prefix="/auth", tags=["auth"])
_dummy_hash = get_password_hash("timing-only-not-an-account-password")

def limit_auth(request, db, action, email=""):
    validate_origin(request)
    address = request.client.host if request.client else "unknown"
    enforce_limit(db, f"auth:{action}:{address}", 30, 900)
    if email:
        enforce_limit(db, f"auth:{action}:{email.lower()}", 10, 900)

@router.post("/register", response_model=Token)
def register(user_in: UserCreate, request: Request, response: Response, db: Session = Depends(get_db)):
    limit_auth(request, db, "register", user_in.email)
    if db.query(User).filter(func.lower(User.email) == user_in.email).first():
        raise HTTPException(400, "An account with this email already exists")
    user = User(name=user_in.name, email=user_in.email, hashed_password=get_password_hash(user_in.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists")
    return create_session(db, user, response)

@router.post("/login", response_model=Token)
def login(user_in: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    limit_auth(request, db, "login", user_in.email)
    user = db.query(User).filter(func.lower(User.email) == user_in.email).first()
    valid = verify_password(user_in.password, user.hashed_password if user else _dummy_hash)
    if not user or not valid:
        raise HTTPException(401, "Invalid credentials")
    if not user.hashed_password.startswith("$argon2"):
        user.hashed_password = get_password_hash(user_in.password)
    previous = request.cookies.get("srs_session")
    if previous:
        db.query(AuthSession).filter_by(token_hash=token_digest(previous)).update({"revoked": True})
    return create_session(db, user, response)

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    request.state.auth_session.revoked = True
    db.commit()
    response.delete_cookie("srs_session", path="/")
    response.delete_cookie("srs_csrf", path="/")

def issue_challenge(db, user, purpose):
    token = secrets.token_urlsafe(48)
    db.query(AuthChallenge).filter_by(user_id=user.id, purpose=purpose, used=False).update({"used": True})
    challenge = AuthChallenge(user_id=user.id, token_hash=token_digest(token), purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=30), used=False)
    db.add(challenge)
    db.commit()
    try:
        deliver_challenge(user.email, token, purpose)
    except Exception:
        challenge.used = True
        db.commit()
        logging.getLogger(__name__).error("Challenge delivery failed; check mail service configuration")

@router.post("/forgot-password")
def forgot_password(data: RecoveryRequest, request: Request, db: Session = Depends(get_db)):
    limit_auth(request, db, "recovery", str(data.email))
    user = db.query(User).filter(func.lower(User.email) == str(data.email).lower()).first()
    if user:
        issue_challenge(db, user, "reset")
    return {"message": "If an account exists, password-reset instructions will be sent."}

@router.post("/request-verification")
def request_verification(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    limit_auth(request, db, "verification", user.email)
    if not user.email_verified:
        issue_challenge(db, user, "verify")
    return {"message": "Verification instructions have been requested."}

def consume_challenge(db, token, purpose):
    challenge = db.query(AuthChallenge).filter_by(token_hash=token_digest(token), purpose=purpose).first()
    if not challenge or challenge.used or challenge.expires_at <= datetime.utcnow():
        raise HTTPException(400, "This link is invalid or has expired")
    claimed = db.execute(update(AuthChallenge).where(AuthChallenge.id == challenge.id, AuthChallenge.used.is_(False)).values(used=True)).rowcount
    if not claimed:
        db.rollback()
        raise HTTPException(400, "This link has already been used")
    return db.get(User, challenge.user_id)

@router.post("/reset-password")
def reset_password(data: ResetPassword, request: Request, db: Session = Depends(get_db)):
    limit_auth(request, db, "reset")
    user = consume_challenge(db, data.token, "reset")
    user.hashed_password = get_password_hash(data.password)
    db.query(AuthSession).filter_by(user_id=user.id).update({"revoked": True})
    db.commit()
    return {"message": "Password updated. Sign in with your new password."}

@router.post("/verify-email")
def verify_email(data: VerifyEmail, request: Request, db: Session = Depends(get_db)):
    limit_auth(request, db, "verify")
    user = consume_challenge(db, data.token, "verify")
    user.email_verified = True
    db.commit()
    return {"message": "Email verified"}
