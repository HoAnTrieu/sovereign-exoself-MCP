import time

from sovereign_exoself_mcp.council import Council
from sovereign_exoself_mcp.domain import CouncilRequest, Route
from sovereign_exoself_mcp.memory import MemoryRepository
from sovereign_exoself_mcp.providers import DeterministicMockProvider
from sovereign_exoself_mcp.settings import Settings


async def test_run_when_mock_then_fast_path(repository: MemoryRepository) -> None:
    council = Council(
        Settings(memory_extraction_enabled=True), repository, DeterministicMockProvider()
    )
    result = await council.run(CouncilRequest(task="Remember project uses mock provider"))
    assert result.status == "ok"
    assert result.route == Route.FAST
    assert result.memory_updates == 0
    assert result.result is not None


async def test_run_when_one_worker_fails_then_is_error(repository: MemoryRepository) -> None:
    provider = DeterministicMockProvider(failure_roles=frozenset({"engineer", "worker"}))
    result = await Council(Settings(), repository, provider).run(
        CouncilRequest(task="Analyze this")
    )
    assert result.status == "error"
    assert any("worker unavailable" in warning for warning in result.warnings)


async def test_run_when_manager_fails_then_returns_structured_error(
    repository: MemoryRepository,
) -> None:
    provider = DeterministicMockProvider(failure_roles=frozenset({"manager"}))
    result = await Council(Settings(), repository, provider).run(
        CouncilRequest(task="Analyze this")
    )
    assert result.status == "error"
    assert "manager unavailable" in result.warnings[0]


async def test_run_when_fast_path_then_skips_critic(repository: MemoryRepository) -> None:
    provider = DeterministicMockProvider()
    result = await Council(Settings(), repository, provider).run(
        CouncilRequest(task="Simple question")
    )
    assert result.status == "ok"
    assert result.route == Route.FAST
    assert result.metrics.model_calls == 2