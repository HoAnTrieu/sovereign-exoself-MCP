import os

import pytest

from sovereign_exoself_mcp.providers import LiteLLMOpenRouterProvider

# Allow runtime override through env for CI/local runs.
OPENROUTER_MODEL = os.environ.get("OPENROUTER_TEST_MODEL", "openrouter/auto")


@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set",
)
async def test_openrouter_when_live_key_configured_then_returns_content() -> None:
    provider = LiteLLMOpenRouterProvider(
        api_key=os.environ["OPENROUTER_API_KEY"],
        model=OPENROUTER_MODEL,
    )

    result = await provider.complete("worker", "Reply with one short word.", 16)

    assert result.content.strip()
    assert result.model
    assert result.input_tokens >= 0
    assert result.output_tokens >= 0
