from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from .core.database import engine
from .core.config import get_settings
from .core.request_limits import RequestSizeLimit
from .routers import auth, projects, findings, traceability, dashboard
from .models import user, project, artifact, finding, traceability as trace_model, llm_log, score, session

settings = get_settings()


@asynccontextmanager
async def lifespan(app):
    if settings.APP_ENV == "production":
        if not settings.COOKIE_SECURE or not settings.PUBLIC_URL.startswith("https://"):
            raise RuntimeError("Production requires HTTPS and COOKIE_SECURE=true")
        if not settings.SMTP_HOST:
            raise RuntimeError("Configure SMTP_HOST for production account recovery")
    yield


app = FastAPI(title="SRS Reviewer API", version="1.1.0", lifespan=lifespan)
app.add_middleware(RequestSizeLimit, maximum=settings.MAX_UPLOAD_SIZE + 1024 * 1024)
app.add_middleware(CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"])
for router in [auth.router, projects.router, findings.router, traceability.router, dashboard.router]:
    app.include_router(router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "SRS Reviewer API", "version": "1.1.0"}


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "healthy"}


@app.get("/ready", tags=["health"])
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            config = Config()
            config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
            if set(MigrationContext.configure(connection).get_current_heads()) != set(ScriptDirectory.from_config(config).get_heads()):
                raise RuntimeError("Migrations pending")
    except Exception:
        raise HTTPException(503, "Database is unavailable or migrations are pending")
    return {"status": "ready"}
