# Troubleshooting

Run `uv run python -m sovereign_exoself_mcp --check` for import/config validation. If tools do not appear, verify the generated host JSON and executable path, then inspect stderr. If FTS5 is unavailable, the server automatically uses token `LIKE` search. If OpenRouter fails, switch to `SOVEREIGN_PROVIDER_MODE=mock` to validate local behavior without credentials.

## Real providers

- The generated host configs (`dist/*.mcp.json*`) now auto-select a real provider: `ollama` by default, `openrouter` when `OPENROUTER_API_KEY` is present. To force a specific mode set `SOVEREIGN_PROVIDER_MODE=mock|ollama|openrouter`.
- `OPENROUTER_API_KEY` is read from the gitignored project `.env` file (never from a version-controlled config). Put `OPENROUTER_API_KEY=sk-or-v1-...` in `.env`.
- To run the live OpenRouter test: `OPENROUTER_API_KEY=sk-or-v1-... uv run pytest tests/integration/test_openrouter_live.py -v`.

## Route overrides

`council_run` accepts either a `mode` of `fast`/`review`/`full` (shorthand) or an explicit `route_override` argument, which always wins when provided.
