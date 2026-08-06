from types import SimpleNamespace

import pytest

from sovereign_exoself_mcp.providers import (
    LiteLLMOllamaProvider,
    OllamaModels,
    ProviderError,
)
from sovereign_exoself_mcp.server import Application
from sovereign_exoself_mcp.settings import Settings


def _models() -> OllamaModels:
    return OllamaModels(
        manager="manager-model",
        worker="worker-model",
        critic="critic-model",
        synthesizer="synthesizer-model",
        archivist="archivist-model",
    )


async def test_ollama_complete_when_successful_then_normalizes_response(monkeypatch) -> None:
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="local answer"))],
            usage=SimpleNamespace(prompt_tokens=11, completion_tokens=4),
            model="qwen2.5-coder:7b",
        )

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    provider = LiteLLMOllamaProvider(
        models=_models(), api_base="http://127.0.0.1:11434", timeout_seconds=7
    )

    result = await provider.complete("engineer", "private prompt", 64)

    assert result.content == "local answer"
    assert result.model == "qwen2.5-coder:7b"
    assert result.input_tokens == 11
    assert result.output_tokens == 4
    assert result.cost is None
    assert len(calls) == 1
    assert calls[0]["model"] == "ollama/worker-model"
    assert calls[0]["messages"][0]["role"] == "system"
    assert len(calls[0]["messages"][0]["content"]) > 0
    assert calls[0]["messages"][1]["role"] == "user"
    assert calls[0]["messages"][1]["content"] == "private prompt"
    assert calls[0]["max_tokens"] == 64
    assert calls[0]["api_base"] == "http://127.0.0.1:11434"
    assert calls[0]["timeout"] == 7


async def test_ollama_complete_when_unavailable_then_raises_clear_error(monkeypatch) -> None:
    async def fake_acompletion(**_kwargs):
        raise OSError("connection refused")

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    provider = LiteLLMOllamaProvider(
        models=_models(), api_base="http://127.0.0.1:11434", timeout_seconds=7
    )

    with pytest.raises(ProviderError, match="Ollama unavailable at http://127.0.0.1:11434"):
        await provider.complete("manager", "prompt", 64)


async def test_ollama_complete_when_timed_out_then_raises_clear_error(monkeypatch) -> None:
    async def fake_acompletion(**_kwargs):
        raise TimeoutError

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    provider = LiteLLMOllamaProvider(
        models=_models(), api_base="http://127.0.0.1:11434", timeout_seconds=7
    )

    with pytest.raises(ProviderError, match="Ollama request timed out after 7 seconds"):
        await provider.complete("manager", "prompt", 64)


def test_application_when_ollama_mode_then_uses_ollama_provider() -> None:
    application = Application(Settings(provider_mode="ollama"))
    assert isinstance(application.provider, LiteLLMOllamaProvider)
    assert application.provider.models.worker == "qwen2.5-coder:7b"
