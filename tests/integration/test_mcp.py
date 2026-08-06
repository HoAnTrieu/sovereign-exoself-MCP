import json
import os
from pathlib import Path

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@pytest.fixture
def server_parameters(tmp_path: Path) -> StdioServerParameters:
    environment = {
        **os.environ,
        "SOVEREIGN_DATA_DIR": str(tmp_path),
        "SOVEREIGN_PROVIDER_MODE": "mock",
        "SOVEREIGN_OLLAMA_API_BASE": "http://127.0.0.1:1",
    }
    return StdioServerParameters(
        command=str(Path.cwd() / ".venv" / "bin" / "python"),
        args=["-m", "sovereign_exoself_mcp"],
        env=environment,
        cwd=str(Path.cwd()),
    )


async def test_mcp_when_connected_then_exposes_exactly_three_tools(
    server_parameters: StdioServerParameters,
) -> None:
    async with stdio_client(server_parameters) as streams, ClientSession(*streams) as session:
        await session.initialize()
        tools = await session.list_tools()
        assert {tool.name for tool in tools.tools} == {
            "council_run",
            "memory_manage",
            "system_status",
        }


async def test_mcp_when_mock_run_then_returns_synthesized_result(
    server_parameters: StdioServerParameters,
) -> None:
    async with stdio_client(server_parameters) as streams, ClientSession(*streams) as session:
        await session.initialize()
        result = await session.call_tool("council_run", {"task": "Analyze the architecture"})
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "ok"
        assert payload["route"] == "fast"
        assert payload["result"] is not None


async def test_mcp_when_status_without_key_then_returns_health(
    server_parameters: StdioServerParameters,
) -> None:
    async with stdio_client(server_parameters) as streams, ClientSession(*streams) as session:
        await session.initialize()
        result = await session.call_tool("system_status", {})
    payload = json.loads(result.content[0].text)
    assert payload["health"] == "ok"
    assert payload["live_openrouter_available"] is False
    assert payload["ollama_available"] is False
    assert payload["ollama_api_base"] == "http://127.0.0.1:1"
    assert payload["ollama_models"] == []
