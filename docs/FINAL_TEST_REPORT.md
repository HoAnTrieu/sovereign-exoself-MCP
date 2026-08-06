# Final Test Report

Date: 2026-08-04. Environment: Linux, CPython 3.14.4, uv 0.12.1. Key installed versions: `mcp 2.0.0`, `litellm 1.95.0`, `aiosqlite 0.22.1`, `pydantic 2.13.4`, `pytest 9.1.1`, `ruff 0.16.1`, `mypy 1.20.2`.

| Command | Result |
|---|---|
| `uv sync --frozen` | passed |
| `uv run ruff format --check .` | passed (29 files) |
| `uv run ruff check .` | passed |
| `uv run mypy src` | passed (9 source files) |
| `uv run pytest` | passed (24 passed, 1 optional live test skipped) |
| `uv run python -m sovereign_exoself_mcp --check` | passed |
| `uv run python scripts/generate_client_configs.py` | passed |
| `bash scripts/smoke_test.sh --mock` | passed (4 passed, 1 optional live test skipped) |
| `OLLAMA_TEST_MODEL=qwen2.5-coder:7b uv run pytest -k "ollama"` | passed (7 selected tests) |
| isolated `UV_PROJECT_ENVIRONMENT=/tmp/opencode/sovereign-exoself-clean-venv uv sync --frozen` plus check | passed |

The stdio integration suite discovered exactly `council_run`, `memory_manage`, and `system_status`; it exercised mock synthesis and no-key `system_status`. The status test used an unavailable local endpoint and still returned health plus `ollama_available`, `ollama_api_base`, and `ollama_models`. Mocked LiteLLM tests cover role-model routing, normalized content/usage, timeout handling, and clear unavailable errors. SQLite persistence, FTS fallback, delete/export, outbox recovery, deduplication, secret filtering, total provider failure, and concurrent workers remain covered. Generated OpenCode and AionUI JSON parse in integration tests and contain absolute local paths.

Live OpenRouter smoke test: blocked because `OPENROUTER_API_KEY` was absent. Optional live Ollama smoke test passed with `qwen2.5-coder:7b`; the normal suite still skips that one test when `OLLAMA_TEST_MODEL` is absent and does not require an Ollama daemon. Local inventory reported `qwen2.5-coder:7b`, `qwen3.5:latest`, `deepseek-r1:latest`, `gemma4:e4b`, and `gpt-oss:latest`. No credentials, prompts, or raw provider responses were recorded. Known limitations: YAML config-file parsing and optional embeddings remain deferred; defaults and environment settings are fully usable today.
