from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Local Multimodal MVP"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_secret_key: str = "change-me"

    database_url: str = "postgresql+psycopg://app:app@localhost:5432/multimodal_mvp"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "chunks"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_vision_model: str | None = None
    vision_answer_enabled: bool = False
    vision_extract_on_ingest: bool = False
    vision_max_images: int = 2
    vision_timeout_seconds: int = 90
    vision_prompt_max_context_chars: int = 3000
    fetch_verify_ssl: bool = True

    evidence_dir: str = "./data/evidence"
    screenshot_dir: str = "./data/evidence/screenshots"
    dom_snapshot_dir: str = "./data/evidence/dom"

    access_token_expire_minutes: int = 480
    refresh_token_expire_minutes: int = 43200
    quality_threshold_chars: int = 300
    retrieval_min_score: float = 0.25

    def ensure_dirs(self) -> None:
        Path(self.evidence_dir).mkdir(parents=True, exist_ok=True)
        Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)
        Path(self.dom_snapshot_dir).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
