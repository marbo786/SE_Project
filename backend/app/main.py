from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

from .core.database import engine, Base
from .core.config import get_settings
from .routers import auth, projects, findings, traceability, dashboard

# Import all models so SQLAlchemy can create their tables
from .models import user, project, artifact, finding, traceability as trace_model, llm_log, score

settings = get_settings()
if settings.SECRET_KEY == "changeme" or "changeme" in settings.SECRET_KEY:
    print("FATAL ERROR: SECRET_KEY cannot be the default placeholder 'changeme'.")
    sys.exit(1)

from alembic import command
from alembic.config import Config
import os
alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
with engine.begin() as connection:
    alembic_cfg.attributes["connection"] = connection
    command.upgrade(alembic_cfg, "head")

app = FastAPI(
    title="SRS Reviewer API",
    description="Automated SRS quality analysis with LLM-assisted checks and traceability",
    version="1.0.0"
)

# CORS configuration - adjust origins for production
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(findings.router)
app.include_router(traceability.router)
app.include_router(dashboard.router)

@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "SRS Reviewer API", "version": "1.0.0"}

@app.get("/health", tags=["health"])
def health_check():
    return {"status": "healthy"}
