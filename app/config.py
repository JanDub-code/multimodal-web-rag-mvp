from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Local Multimodal MVP"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_secret_key: str = "change-me"

    database_url: str = "postgresql+psycopg://app:app@localhost:5432/multimodal_mvp"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "chunks_qwen3_embedding_8b_4096"

    embedding_base_url: str = Field(
        default="http://127.0.0.1:11434",
        validation_alias=AliasChoices("EMBEDDING_BASE_URL", "OLLAMA_EMBEDDING_BASE_URL"),
    )
    embedding_model: str = "qwen3-embedding:8b"
    embedding_dimensions: int = 4096
    embedding_timeout_seconds: int = 60
    llm_base_url: str = Field(
        default="http://127.0.0.1:1234/v1",
        validation_alias=AliasChoices("LLM_BASE_URL", "OPENAI_BASE_URL", "OLLAMA_URL"),
    )
    llm_api_key: str = Field(
        default="lm-studio",
        validation_alias=AliasChoices("LLM_API_KEY", "OPENAI_API_KEY"),
    )
    llm_model: str = Field(
        default="qwen/qwen3.5-2b",
        validation_alias=AliasChoices("LLM_MODEL", "OPENAI_MODEL", "OLLAMA_MODEL"),
    )
    llm_vision_model: str | None = Field(
        default="qwen/qwen3.5-2b",
        validation_alias=AliasChoices("LLM_VISION_MODEL", "OPENAI_VISION_MODEL", "OLLAMA_VISION_MODEL"),
    )
    vision_answer_enabled: bool = True
    vision_extract_on_ingest: bool = True
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
    compliance_enforcement: bool = False

    refresh_default_interval_minutes: int = 10080
    refresh_retry_backoff_minutes: int = 30
    refresh_scheduler_enabled: bool = False
    refresh_scheduler_interval_seconds: int = 900
    refresh_scheduler_batch_size: int = 5

    def ensure_dirs(self) -> None:
        Path(self.evidence_dir).mkdir(parents=True, exist_ok=True)
        Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)
        Path(self.dom_snapshot_dir).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
