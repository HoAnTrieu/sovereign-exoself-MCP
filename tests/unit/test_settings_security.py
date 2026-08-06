from sovereign_exoself_mcp.domain import CouncilRequest
from sovereign_exoself_mcp.providers import ProviderError, is_retryable
from sovereign_exoself_mcp.security import contains_secret, redact
from sovereign_exoself_mcp.settings import Settings


def test_settings_when_environment_override_then_uses_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SOVEREIGN_DATA_DIR", str(tmp_path))
    assert Settings().database_path == tmp_path / "memory.sqlite3"


def test_settings_when_default_then_uses_local_ollama_defaults() -> None:
    settings = Settings()
    assert settings.provider_mode == "mock"
    assert settings.ollama_api_base == "http://127.0.0.1:11434"
    assert settings.ollama_manager_model == "granite3.3:2b"
    assert settings.ollama_worker_model == "qwen2.5-coder:7b"
    assert settings.ollama_critic_model == "qwen2.5-coder:7b"
    assert settings.ollama_synthesizer_model == "granite3.3:2b"
    assert settings.ollama_archivist_model == "granite3.3:2b"
    assert settings.max_concurrent_workers == 1


def test_settings_when_ollama_environment_override_then_uses_environment(monkeypatch) -> None:
    monkeypatch.setenv("SOVEREIGN_PROVIDER_MODE", "ollama")
    monkeypatch.setenv("SOVEREIGN_OLLAMA_API_BASE", "http://127.0.0.1:22434")
    monkeypatch.setenv("SOVEREIGN_OLLAMA_WORKER_MODEL", "gpt-oss:latest")
    settings = Settings()
    assert settings.provider_mode == "ollama"
    assert settings.ollama_api_base == "http://127.0.0.1:22434"
    assert settings.ollama_worker_model == "gpt-oss:latest"


def test_request_when_task_too_long_then_rejects() -> None:
    from pydantic import ValidationError

    try:
        CouncilRequest(task="x" * 8001)
    except ValidationError:
        return
    raise AssertionError("expected validation error")


def test_redaction_when_secret_then_masks_value() -> None:
    assert redact("token=abc123") == "[REDACTED]"
    assert contains_secret("Bearer=abc123") is True


def test_retry_when_transient_then_true() -> None:
    assert is_retryable(ProviderError("temporary", transient=True)) is True
    assert is_retryable(ProviderError("invalid", transient=False)) is False
