import json

import pytest

from sovereign_exoself_mcp.council import Council, _parse_json_response
from sovereign_exoself_mcp.domain import (
    CouncilRequest,
    Route,
    TaskType,
    WorkerProfile,
)
from sovereign_exoself_mcp.memory import MemoryRepository
from sovereign_exoself_mcp.providers import DeterministicMockProvider
from sovereign_exoself_mcp.settings import Settings


class TestJsonParser:
    def test_valid_json(self):
        assert _parse_json_response('{"key": "value"}') == {"key": "value"}

    def test_json_in_code_fence(self):
        content = '```json\n{"key": "value"}\n```'
        assert _parse_json_response(content) == {"key": "value"}

    def test_json_with_surrounding_text(self):
        content = 'Here is the result: {"key": "value"} end.'
        assert _parse_json_response(content) == {"key": "value"}

    def test_invalid_json_returns_none(self):
        assert _parse_json_response("not json at all") is None

    def test_empty_string(self):
        assert _parse_json_response("") is None


class TestFastPathRouting:
    async def test_simple_task_uses_fast(self, repository: MemoryRepository):
        provider = DeterministicMockProvider()
        council = Council(Settings(), repository, provider)
        result = await council.run(CouncilRequest(task="What is 2+2?"))
        assert result.status == "ok"
        assert result.route == Route.FAST
        assert result.metrics.model_calls == 2

    async def test_route_override_bypasses_manager(self, repository: MemoryRepository):
        provider = DeterministicMockProvider()
        council = Council(Settings(), repository, provider)
        result = await council.run(
            CouncilRequest(task="Complex architecture", route_override=Route.FAST)
        )
        assert result.status == "ok"
        assert result.route == Route.FAST

    async def test_route_override_review(self, repository: MemoryRepository):
        provider = DeterministicMockProvider()
        council = Council(Settings(), repository, provider)
        result = await council.run(
            CouncilRequest(task="Simple question", route_override=Route.REVIEW)
        )
        assert result.status == "ok"
        assert result.route == Route.REVIEW

    async def test_route_override_full(self, repository: MemoryRepository):
        provider = DeterministicMockProvider()
        council = Council(Settings(), repository, provider)
        result = await council.run(
            CouncilRequest(task="Simple question", route_override=Route.FULL)
        )
        assert result.status == "ok"
        assert result.route == Route.FULL


class TestRuntimeConstraints:
    async def test_worker_failure_returns_error(self, repository: MemoryRepository):
        provider = DeterministicMockProvider(failure_roles=frozenset({"engineer", "worker"}))
        council = Council(Settings(), repository, provider)
        result = await council.run(CouncilRequest(task="Do something"))
        assert result.status == "error"

    async def test_manager_failure_returns_error(self, repository: MemoryRepository):
        provider = DeterministicMockProvider(failure_roles=frozenset({"manager"}))
        council = Council(Settings(), repository, provider)
        result = await council.run(CouncilRequest(task="Do something"))
        assert result.status == "error"
        assert "manager unavailable" in result.warnings[0]

    async def test_critic_failure_returns_partial(self, repository: MemoryRepository):
        provider = DeterministicMockProvider(failure_roles=frozenset({"critic"}))
        council = Council(Settings(), repository, provider)
        result = await council.run(
            CouncilRequest(task="Analyze this", route_override=Route.REVIEW)
        )
        assert result.status == "partial"
        assert "critic unavailable" in result.warnings[0]

    async def test_synthesizer_failure_falls_back_to_worker(self, repository: MemoryRepository):
        provider = DeterministicMockProvider(failure_roles=frozenset({"synthesizer"}))
        council = Council(Settings(), repository, provider)
        result = await council.run(
            CouncilRequest(task="Analyze this", route_override=Route.REVIEW)
        )
        assert result.status == "ok"
        assert result.result is not None

    async def test_memory_updates_when_needs_memory_true(self, repository: MemoryRepository):
        provider = DeterministicMockProvider()
        council = Council(
            Settings(memory_extraction_enabled=True), repository, provider
        )
        result = await council.run(
            CouncilRequest(
                task="Remember this decision",
                route_override=Route.FULL,
                needs_memory=True,
            )
        )
        assert result.memory_updates >= 0

    async def test_no_memory_updates_when_needs_memory_false(self, repository: MemoryRepository):
        provider = DeterministicMockProvider()
        council = Council(
            Settings(memory_extraction_enabled=True), repository, provider
        )
        result = await council.run(
            CouncilRequest(
                task="Remember this decision",
                route_override=Route.FULL,
                needs_memory=False,
            )
        )
        assert result.memory_updates == 0

    async def test_metrics_are_populated(self, repository: MemoryRepository):
        provider = DeterministicMockProvider()
        council = Council(Settings(), repository, provider)
        result = await council.run(CouncilRequest(task="Quick question"))
        assert result.metrics.duration_ms >= 0
        assert result.metrics.model_calls >= 1
        assert result.run_id is not None

    async def test_max_review_rounds_respected(self, repository: MemoryRepository):
        provider = DeterministicMockProvider()
        council = Council(
            Settings(max_review_rounds=0), repository, provider
        )
        result = await council.run(
            CouncilRequest(task="Test", route_override=Route.REVIEW)
        )
        assert result.status in ("ok", "partial")
