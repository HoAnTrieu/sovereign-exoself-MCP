import json

import pytest

from sovereign_exoself_mcp.domain import MemoryKind
from sovereign_exoself_mcp.memory import MemoryRepository, fingerprint


def test_fingerprint_when_whitespace_differs_then_equal() -> None:
    assert fingerprint("Prefer  concise answers") == fingerprint("prefer concise answers")


async def test_store_when_duplicate_then_reuses_record(repository: MemoryRepository) -> None:
    first_id, inserted = await repository.store("Prefer concise answers", MemoryKind.PREFERENCE)
    second_id, duplicate = await repository.store(" prefer concise answers ", MemoryKind.PREFERENCE)
    assert inserted is True
    assert duplicate is False
    assert first_id == second_id


async def test_search_when_fts_unavailable_then_uses_fallback(tmp_path) -> None:
    repository = MemoryRepository(tmp_path / "fallback.sqlite3", fts_enabled=False)
    await repository.open()
    try:
        await repository.store("Project uses SQLite WAL", MemoryKind.PROJECT)
        records = await repository.search("SQLite", 5)
        assert [record.content for record in records] == ["Project uses SQLite WAL"]
    finally:
        await repository.close()


async def test_delete_and_export_when_record_exists_then_persists(
    repository: MemoryRepository,
) -> None:
    memory_id, _ = await repository.store("Use mock testing", MemoryKind.INSTRUCTION)
    assert await repository.delete(memory_id) is True
    assert json.loads(await repository.export()) == []


async def test_outbox_when_reopened_then_processes_once(tmp_path) -> None:
    path = tmp_path / "outbox.sqlite3"
    repository = MemoryRepository(path)
    await repository.open()
    await repository.enqueue(
        "memory_store", '{"content":"Remember mock mode","kind":"instruction"}'
    )
    await repository.close()
    restarted = MemoryRepository(path)
    await restarted.open()
    try:
        assert len(await restarted.search("mock", 5)) == 1
        assert await restarted.process_outbox() == 0
    finally:
        await restarted.close()


async def test_store_when_secret_then_rejects(repository: MemoryRepository) -> None:
    with pytest.raises(ValueError, match="secret"):
        await repository.store("api_key=top-secret", MemoryKind.FACT)
