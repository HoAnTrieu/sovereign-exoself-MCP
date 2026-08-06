"""End-to-end MCP feature tests via a real stdio client.

These tests exercise the full set of features that the `sovereign-exoself`
skill instructs an agent to use, over a real MCP server started through
stdio. They follow the same pattern as `test_mcp.py` (each test opens and
closes its own stdio session inside the test body) so they play nicely with
pytest-asyncio. They are hermetic: the server runs in `mock` provider mode
with an isolated temp database, so no API key or external service is needed.
"""

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
        "SOVEREIGN_MEMORY_EXTRACTION_ENABLED": "false",
    }
    # Strip any live credentials so the status assertions are deterministic.
    environment.pop("OPENROUTER_API_KEY", None)
    return StdioServerParameters(
        command=str(Path.cwd() / ".venv" / "bin" / "python"),
        args=["-m", "sovereign_exoself_mcp"],
        env=environment,
        cwd=str(Path.cwd()),
    )


async def _invoke(
    server_parameters: StdioServerParameters,
    name: str,
    args: dict,
) -> dict:
    async with stdio_client(server_parameters) as streams, ClientSession(*streams) as session:
        await session.initialize()
        result = await session.call_tool(name, args)
    return json.loads(result.content[0].text)


# --- system_status ----------------------------------------------------------


async def test_status_exposes_expected_inventory(server_parameters: StdioServerParameters) -> None:
    payload = await _invoke(server_parameters, "system_status", {})
    assert payload["health"] == "ok"
    assert payload["provider_mode"] == "mock"
    assert payload["live_openrouter_available"] is False
    assert payload["ollama_available"] is False
    assert payload["database_schema_version"] == 1
    # Model mapping must be fully populated for every council role.
    assert set(payload["model_mapping"]) == {
        "manager",
        "worker",
        "critic",
        "synthesizer",
        "archivist",
    }


async def test_status_exposes_tools(server_parameters: StdioServerParameters) -> None:
    async with stdio_client(server_parameters) as streams, ClientSession(*streams) as session:
        await session.initialize()
        tools = await session.list_tools()
        assert {tool.name for tool in tools.tools} == {
            "council_run",
            "memory_manage",
            "system_status",
        }


# --- council_run ------------------------------------------------------------


async def test_council_fast_route(server_parameters: StdioServerParameters) -> None:
    payload = await _invoke(
        server_parameters,
        "council_run",
        {"task": "Summarize the project in one line.", "mode": "auto", "budget": "low"},
    )
    assert payload["status"] == "ok"
    assert payload["route"] == "fast"
    assert payload["result"] is not None
    assert payload["metrics"]["model_calls"] == 2  # manager + worker


async def test_council_review_route(server_parameters: StdioServerParameters) -> None:
    payload = await _invoke(
        server_parameters,
        "council_run",
        {
            "task": "Review this snippet.",
            "mode": "analysis",
            "budget": "balanced",
            "route_override": "review",
        },
    )
    assert payload["status"] == "ok"
    assert payload["route"] == "review"
    assert payload["metrics"]["model_calls"] >= 3  # manager + worker + critic


async def test_council_full_route_with_worker_profile(
    server_parameters: StdioServerParameters,
) -> None:
    payload = await _invoke(
        server_parameters,
        "council_run",
        {
            "task": "Design a module API.",
            "mode": "analysis",
            "budget": "deep",
            "route_override": "full",
            "worker_profile": "code_engineer",
        },
    )
    assert payload["status"] == "ok"
    assert payload["route"] == "full"
    assert payload["models"]  # per-role model map present
    # full route runs manager + worker + critic + synthesizer
    assert payload["metrics"]["model_calls"] >= 4


async def test_council_returns_run_id_and_metrics(server_parameters: StdioServerParameters) -> None:
    payload = await _invoke(
        server_parameters,
        "council_run",
        {"task": "Give a bounded fact.", "output_format": "text"},
    )
    assert payload["run_id"]
    assert payload["metrics"]["duration_ms"] >= 0
    assert payload["metrics"]["input_tokens"] >= 0
    assert payload["metrics"]["output_tokens"] >= 0


# --- memory_manage ----------------------------------------------------------


async def test_memory_store_search_list(server_parameters: StdioServerParameters) -> None:
    store = await _invoke(
        server_parameters,
        "memory_manage",
        {"action": "store", "content": "Use mock testing", "kind": "instruction"},
    )
    assert store["inserted"] is True
    assert store["id"]

    found = await _invoke(
        server_parameters, "memory_manage", {"action": "search", "query": "mock", "limit": 5}
    )
    assert any(item["content"] == "Use mock testing" for item in found["items"])

    listed = await _invoke(server_parameters, "memory_manage", {"action": "list", "limit": 10})
    assert list(listed["items"])  # non-empty


async def test_memory_export_and_delete(server_parameters: StdioServerParameters) -> None:
    store = await _invoke(
        server_parameters,
        "memory_manage",
        {"action": "store", "content": "Temporary record", "kind": "fact"},
    )
    memory_id = store["id"]

    exported = await _invoke(server_parameters, "memory_manage", {"action": "export"})
    assert "Temporary record" in exported["json"]

    deleted = await _invoke(
        server_parameters, "memory_manage", {"action": "delete", "memory_id": memory_id}
    )
    assert deleted["deleted"] is True

    export_after = await _invoke(server_parameters, "memory_manage", {"action": "export"})
    assert "Temporary record" not in export_after["json"]


async def test_memory_profile(server_parameters: StdioServerParameters) -> None:
    profile = await _invoke(server_parameters, "memory_manage", {"action": "profile"})
    assert "count" in profile
    assert "kinds" in profile
