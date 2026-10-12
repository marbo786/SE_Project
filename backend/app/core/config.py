from pydantic_settings import BaseSettings
from functools import lru_cache
import yaml
import os

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
    LLM_MODEL: str = "llama-3.1-8b-instant"
    DATABASE_URL: str = "sqlite:///./srs_reviewer.db"
    CORS_ORIGINS: str = "http://localhost:5173"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB

    class Config:
        env_file = _env_file_path
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

def load_yaml_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "../../config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

_yaml_config: dict | None = None

def get_yaml_config() -> dict:
    global _yaml_config
    if _yaml_config is None:
        _yaml_config = load_yaml_config()
    return _yaml_config
