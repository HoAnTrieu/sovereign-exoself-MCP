from pathlib import Path

import pytest

from sovereign_exoself_mcp.memory import MemoryRepository


@pytest.fixture
async def repository(tmp_path: Path) -> MemoryRepository:
    repo = MemoryRepository(tmp_path / "memory.sqlite3")
    await repo.open()
    yield repo
    await repo.close()
