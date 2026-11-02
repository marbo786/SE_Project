from datetime import datetime
import secrets
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .database import get_db
from .config import get_settings
from .security import token_digest
from ..models.user import User
from ..models.project import Project
from ..models.session import AuthSession


def validate_origin(request: Request):
    origin = request.headers.get("origin")
    settings = get_settings()
    allowed = {o.strip().rstrip("/") for o in settings.CORS_ORIGINS.split(",")}
    allowed.add(settings.PUBLIC_URL.rstrip("/"))
    if origin and origin.rstrip("/") not in allowed:
        raise HTTPException(403, "Request origin is not allowed")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    authorization = request.headers.get("authorization", "")
    bearer = authorization[7:] if authorization.lower().startswith("bearer ") else None
    token = bearer or request.cookies.get("srs_session")
    if not token or len(token) > 256:
        raise HTTPException(401, "Sign in to continue")
    session = db.query(AuthSession).filter(AuthSession.token_hash == token_digest(token),
        AuthSession.revoked.is_(False), AuthSession.expires_at > datetime.utcnow()).first()
    if not session:
        raise HTTPException(401, "Your session expired. Please sign in again.")
    if not bearer and request.method not in {"GET", "HEAD", "OPTIONS"}:
        validate_origin(request)
        csrf = request.headers.get("x-csrf-token", "")
        if not csrf or not secrets.compare_digest(token_digest(csrf), session.csrf_hash):
            raise HTTPException(403, "Invalid request verification token")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, "Sign in to continue")
    request.state.auth_session = session
    return user


def require_project_access(db: Session, user: User, project_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    return project
