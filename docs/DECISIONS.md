# Decisions

- Python 3.14.4 is used because all selected dependencies installed and tests ran under it.
- MCP Python SDK 2.0.0 uses `MCPServer` and `run_stdio_async`; legacy FastMCP imports are not used.
- AnyIO task groups provide structured concurrency; the mock provider makes it deterministic.
- SQLite WAL plus FTS5 avoids external infrastructure. Embeddings are deliberately optional and absent in v1.
- OpenRouter owns model/provider fallback. Local retries apply only to normalized transient failures.
