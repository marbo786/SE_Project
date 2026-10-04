from pydantic_settings import BaseSettings
from functools import lru_cache
import yaml
import os

class Settings(BaseSettings):
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GROQ_API_KEY: str = ""
    LLM_PROVIDER: str = "mock"
    DATABASE_URL: str = "sqlite:///./srs_reviewer.db"

    class Config:
        env_file = "backend/.env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

def load_yaml_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "../../config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

_yaml_config: dict | None = None

def get_yaml_config() -> dict:
    global _yaml_config
    if _yaml_config is None:
        _yaml_config = load_yaml_config()
    return _yaml_config
