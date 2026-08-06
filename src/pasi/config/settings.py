"""Runtime settings loaded from environment / `.env`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_repo_root() -> Path:
    """Walk parents until `pyproject.toml` is found; fallback to CWD."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


class Settings(BaseSettings):
    """Process-level settings. Research YAML lives under `configs/`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PASI_",
        extra="ignore",
    )

    env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    data_dir: Path = Field(default=Path("data"))
    db_path: Path = Field(default=Path("db/pasi.sqlite"))
    duckdb_path: Path = Field(default=Path("db/pasi.duckdb"))
    configs_dir: Path = Field(default=Path("configs"))
    logs_dir: Path = Field(default=Path("logs"))
    prompts_dir: Path = Field(default=Path("prompts"))
    llm_api_key: str | None = Field(default=None)
    llm_provider: str = Field(
        default="openai",
        description="LLM provider: openai | gemini",
    )

    # OpenAI (paid / trial credits)
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key; falls back to llm_api_key if unset",
    )
    openai_model: str = Field(default="gpt-4o-mini")
    openai_temperature: float = Field(default=0.0)
    openai_max_input_chars: int = Field(
        default=60_000,
        description="Max characters of clean text sent to the model",
    )

    # Google Gemini (AI Studio free tier)
    gemini_api_key: str | None = Field(default=None)
    gemini_model: str = Field(default="gemini-flash-latest")

    # HTTP / SEC EDGAR — SEC requires a descriptive User-Agent with contact email.
    sec_user_agent: str = Field(
        default="PASI Academic Research contact@example.com",
        description="User-Agent sent to SEC and other HTTP endpoints",
    )
    http_timeout_seconds: float = Field(default=60.0)
    http_max_retries: int = Field(default=3)
    http_request_delay_seconds: float = Field(default=0.25)

    @property
    def repo_root(self) -> Path:
        return find_repo_root()

    def resolve(self, path: Path) -> Path:
        """Resolve a project-relative path against the repo root."""
        if path.is_absolute():
            return path
        return self.repo_root / path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
