# Current Status

## Completed

Package, SQLite WAL/FTS/outbox repository, mock/OpenRouter/Ollama provider seam, bounded council, three MCP tools, generated host configs, tests, and validation scripts.

## In Progress

None.

## Remaining

Only an optional live OpenRouter smoke test requiring a credential.

## Latest Validation

`uv sync --frozen`, Ruff format/check, Mypy, 18 pytest tests, MCP check, config generation, and 4-test mock smoke suite passed on 2026-08-03.

**2026-08-06 — Real-provider config generation.** `scripts/generate_client_configs.py` no longer hardcodes `SOVEREIGN_PROVIDER_MODE=mock`. It now auto-selects a real provider when generating host configs:
- `ollama` (default) when no `OPENROUTER_API_KEY` is present,
- `openrouter` when `OPENROUTER_API_KEY` is set,
- `mock` only if explicitly requested via `SOVEREIGN_PROVIDER_MODE`.

Both generated snippets (`dist/aionui.mcp.json`, `dist/opencode.mcp.jsonc`) now launch the server with `SOVEREIGN_PROVIDER_MODE=ollama`. A live end-to-end `council_run` against Ollama succeeded (route `fast`, worker `qwen2.5-coder:7b`). Live Ollama integration test (`tests/integration/test_ollama_live.py`) passes.

**2026-08-06 — Secrets are environment-only.** `OPENROUTER_API_KEY` is now read from the gitignored project `.env` file via `sovereign_exoself_mcp.settings.load_env_file()`. The generated host configs never embed the key; the server loads it only when the `openrouter` provider is selected. `.gitignore` covers `.env`, `apikey.txt`, and `*.bak`.

**2026-08-06 — Route override fix.** `council_run` previously ignored its `route_override` argument (it was shadowed to `None` inside the handler and not exposed in the tool signature). It is now exposed and respected: an explicit `route_override` always wins over `mode` shorthand. Covered by `tests/integration/test_mcp_full_features.py`.

**2026-08-06 — Feature-complete live MCP tests.** Added `tests/integration/test_mcp_full_features.py` (9 tests) exercising all skill-facing features over a real stdio MCP server: `system_status` inventory + available tools, `council_run` across `fast`/`review`/`full` routes with worker profiles and metrics, and `memory_manage` for `store`/`search`/`list`/`export`/`delete`/`profile`. Also added `tests/integration/test_openrouter_live.py` (live, credential-gated). Full suite: **85 passed, 2 skipped** (the skipped are credential-gated live tests). Ruff and Mypy both clean.

## Known Blockers

None. Ollama mode runs out of the box; OpenRouter runs when `OPENROUTER_API_KEY` is present in `.env`.

## Next Safe Action

Use the generated MCP snippets (they run the real Ollama provider), or run `bash scripts/test.sh` after changes.
