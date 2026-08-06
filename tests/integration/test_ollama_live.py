import os

import pytest

from sovereign_exoself_mcp.providers import LiteLLMOllamaProvider, OllamaModels
from sovereign_exoself_mcp.settings import Settings


@pytest.mark.skipif(not os.environ.get("OLLAMA_TEST_MODEL"), reason="OLLAMA_TEST_MODEL not set")
async def test_ollama_when_live_model_configured_then_returns_content() -> None:
    model = os.environ["OLLAMA_TEST_MODEL"]
    settings = Settings()
    provider = LiteLLMOllamaProvider(
        models=OllamaModels(
            manager=model,
            worker=model,
            critic=model,
            synthesizer=model,
            archivist=model,
        ),
        api_base=settings.ollama_api_base,
        timeout_seconds=settings.provider_timeout_seconds,
    )

    result = await provider.complete("worker", "Reply with one short word.", 16)

    assert result.content.strip()
