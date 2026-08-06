"""Settings and XDG path resolution."""

import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_env_file() -> None:
    """Best-effort load a project-root `.env` into the process environment.

    `.env` is gitignored and intended to hold local secrets such as
    ``OPENROUTER_API_KEY``. Environment variables that are already set take
    precedence (we never override an explicit value). This keeps secrets
    environment-only and out of any version-controlled configuration file.
    """
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _xdg(name: str, fallback: str) -> Path:
    """Return a per-user XDG path without creating it."""
    import os

    return Path(os.environ.get(name, str(Path.home() / fallback))) / "sovereign-exoself-mcp"


class Settings(BaseSettings):
    """Environment-overridable application settings."""

    model_config = SettingsConfigDict(env_prefix="SOVEREIGN_", extra="ignore")

    provider_mode: Literal["mock", "openrouter", "ollama"] = "mock"
    data_dir: Path = Field(default_factory=lambda: _xdg("XDG_DATA_HOME", ".local/share"))
    state_dir: Path = Field(default_factory=lambda: _xdg("XDG_STATE_HOME", ".local/state"))
    config_path: Path | None = None
    log_level: str = "INFO"
    max_concurrent_workers: int = Field(default=1, ge=1, le=4)
    memory_limit: int = Field(default=5, ge=1, le=20)
    provider_timeout_seconds: float = Field(default=120, gt=0, le=120)
    ollama_api_base: str = "http://127.0.0.1:11434"
    ollama_manager_model: str = "granite3.3:2b"
    ollama_worker_model: str = "qwen2.5-coder:7b"
    ollama_critic_model: str = "qwen2.5-coder:7b"
    ollama_synthesizer_model: str = "granite3.3:2b"
    ollama_archivist_model: str = "granite3.3:2b"
    retry_limit: int = Field(default=2, ge=0, le=5)
    mock_delay_seconds: float = Field(default=0, ge=0, le=10)
    mock_failure_roles: str = ""
    memory_extraction_enabled: bool = True
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    think: bool = Field(default=False)
    default_route: Literal["auto", "fast", "review", "full"] = "auto"
    allow_fast_path: bool = True
    allow_review_path: bool = True
    allow_full_council: bool = True
    max_review_rounds: int = Field(default=1, ge=0, le=3)
    max_council_rounds: int = Field(default=2, ge=1, le=5)
    stop_on_approve: bool = True
    stop_on_valid_fast_result: bool = True
    context_manager: int = Field(default=4096, ge=1024, le=32768)
    context_worker: int = Field(default=8192, ge=1024, le=65536)
    context_critic: int = Field(default=8192, ge=1024, le=65536)
    context_synthesizer: int = Field(default=4096, ge=1024, le=32768)
    context_archivist: int = Field(default=4096, ge=1024, le=32768)

    @property
    def database_path(self) -> Path:
        """Return the durable SQLite path."""
        return self.data_dir / "memory.sqlite3"