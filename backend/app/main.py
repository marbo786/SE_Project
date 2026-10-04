from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.database import engine, Base
from .routers import auth, projects, findings, traceability, dashboard

# Import all models so SQLAlchemy can create their tables
from .models import user, project, artifact, finding, traceability as trace_model, llm_log, score

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SRS Reviewer API",
    description="Automated SRS quality analysis with LLM-assisted checks and traceability",
    version="1.0.0"
)

# CORS configuration - adjust origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
