# Architecture

The stdio MCP boundary exposes three tools: `council_run`, `memory_manage`, and `system_status`.

## Council Routing

`Council` owns a three-route decision flow:

1. **Manager** (granite3.3:2b) — classifies task, selects route and worker profile, returns structured `ManagerDecision`.
2. **Router** — selects path based on manager decision:
   - `FAST` — worker only. Used for simple questions, facts, quick analysis.
   - `REVIEW` — worker → critic → synthesizer. Used when quality verification needed.
   - `FULL` — worker → critic → synthesizer → archivist. Used for complex tasks requiring memory extraction.
3. **Worker** (qwen2.5-coder:7b) — executes task with role-specific system prompt and optional worker profile.
4. **Critic** (qwen2.5-coder:7b) — reviews worker output, returns `APPROVE`/`REJECT` verdict with issues.
5. **Synthesizer** (granite3.3:2b) — merges worker + critic outputs into final result.
6. **Archivist** (granite3.3:2b) — extracts memory items from completed runs.

## Provider Boundary

`Provider` isolates mock and LiteLLM/Ollama implementations. All providers accept a `profile` parameter for worker role specialization. `DeterministicMockProvider` returns valid JSON for all roles to support deterministic testing.

## Memory

`MemoryRepository` owns migrations, WAL, FTS5/fallback search, transactions, and outbox recovery. No provider response reaches the repository without normalized internal models via Pydantic schemas in `domain.py`.

## Prompt System

Prompts are loaded from `prompts/*.txt` files via `prompts.py`:
- `common.txt` — shared instructions for all roles
- `manager.txt` — routing and classification instructions
- `worker.txt` — task execution instructions
- `critic.txt` — quality review instructions
- `synthesizer.txt` — result synthesis instructions
- `archivist.txt` — memory extraction instructions
- `profiles/*.txt` — worker specialization profiles (code_engineer, system_engineer, etc.)

Each prompt file includes a version header tracked in `PROMPT_VERSIONS` for observability.