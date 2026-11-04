from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import yaml
import os
from contextvars import ContextVar

run_config = ContextVar("run_config", default=None)

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
_backend_env = os.path.join(_backend_dir, ".env")
_root_env = os.path.abspath(os.path.join(_backend_dir, "..", ".env"))
_env_file_path = _backend_env if os.path.exists(_backend_env) else (_root_env if os.path.exists(_root_env) else ".env")

class Settings(BaseSettings):
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GROQ_API_KEY: str = ""
    LLM_PROVIDER: str = "mock"
    LLM_MODEL: str = "qwen/qwen3.8-27b"
    DATABASE_URL: str = "sqlite:///./srs_reviewer.db"
    CORS_ORIGINS: str = "http://localhost:5173"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    MAX_DOCUMENT_PAGES: int = 100
    MAX_DOCUMENT_CHARACTERS: int = 1_000_000
    MAX_REQUIREMENTS: int = 1000
    MAX_UML_ELEMENTS: int = 2000
    MAX_EXPANDED_SIZE: int = 50 * 1024 * 1024
    PARSER_TIMEOUT_SECONDS: int = 20
    PARSER_MEMORY_MB: int = 512
    MAX_PROJECTS_PER_USER: int = 100
    APP_ENV: str = "development"
    COOKIE_SECURE: bool = False
    PUBLIC_URL: str = "http://localhost:5173"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@example.com"
    MAIL_SINK_DIR: str = "./mail_sink"

    model_config = SettingsConfigDict(env_file=_env_file_path, env_file_encoding="utf-8", extra="ignore")

@lru_cache()
def get_settings() -> Settings:
    return Settings()

def load_yaml_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "../../config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

_yaml_config: dict | None = None

def get_yaml_config() -> dict:
    if run_config.get() is not None:
        return run_config.get()
    global _yaml_config
    if _yaml_config is None:
        _yaml_config = load_yaml_config()
    return _yaml_config
