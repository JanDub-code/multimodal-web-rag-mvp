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
    qdrant_collection: str = "chunks_fastembed_multilingual_minilm_384"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimensions: int = 384
    default_generation_model: str = Field(
        default="opencode-go/deepseek-v4-flash",
        validation_alias=AliasChoices("DEFAULT_GENERATION_MODEL"),
    )
    vision_generation_model: str = Field(
        default="opencode-go/kimi-k2.5",
        validation_alias=AliasChoices("VISION_GENERATION_MODEL"),
    )
    generation_provider: str = Field(
        default="opencode_go",
        validation_alias=AliasChoices("GENERATION_PROVIDER"),
    )
    opencode_api_key_runtime: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENCODE_API_KEY_RUNTIME"),
    )
    opencode_go_base_url: str = Field(
        default="https://opencode.ai/zen/go/v1",
        validation_alias=AliasChoices("OPENCODE_GO_BASE_URL"),
    )
    opencode_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENCODE_API_KEY"),
    )
    vision_max_images: int = 2
    vision_timeout_seconds: int = 90
    vision_prompt_max_context_chars: int = 3000
    vision_extract_on_ingest: bool = False
    fetch_verify_ssl: bool = True

    evidence_dir: str = "./data/evidence"
    screenshot_dir: str = "./data/evidence/screenshots"
    dom_snapshot_dir: str = "./data/evidence/dom"

    access_token_expire_minutes: int = 480
    refresh_token_expire_minutes: int = 43200
    quality_threshold_chars: int = 300
    retrieval_min_score: float = 0.25
    retrieval_warmup_on_startup: bool = False
    compliance_enforcement: bool = False

    def ensure_dirs(self) -> None:
        Path(self.evidence_dir).mkdir(parents=True, exist_ok=True)
        Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)
        Path(self.dom_snapshot_dir).mkdir(parents=True, exist_ok=True)

    def model_post_init(self, __context: object) -> None:
        runtime_key = (self.opencode_api_key_runtime or "").strip()
        file_key = (self.opencode_api_key or "").strip()

        invalid_placeholders = {
            "OPENCODE_API_KEY_RUNTIME",
            "${OPENCODE_API_KEY_RUNTIME}",
            "$OPENCODE_API_KEY_RUNTIME",
        }
        if runtime_key in invalid_placeholders:
            runtime_key = ""
        if file_key in invalid_placeholders:
            file_key = ""

        self.opencode_api_key = runtime_key or file_key or None


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
