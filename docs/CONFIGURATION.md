# Configuration

Environment has precedence over YAML/example defaults. `SOVEREIGN_PROVIDER_MODE` accepts `mock`, `openrouter`, or `ollama`; deterministic `mock` remains the default. OpenRouter is optional and reads `OPENROUTER_API_KEY` only when selected. Ollama is also optional, local, and never requires `OPENROUTER_API_KEY`.

Ollama settings:

| Environment variable | Default |
|---|---|
| `SOVEREIGN_OLLAMA_API_BASE` | `http://127.0.0.1:11434` |
| `SOVEREIGN_OLLAMA_MANAGER_MODEL` | `qwen3.5:latest` |
| `SOVEREIGN_OLLAMA_WORKER_MODEL` | `qwen2.5-coder:7b` |
| `SOVEREIGN_OLLAMA_CRITIC_MODEL` | `deepseek-r1:latest` |
| `SOVEREIGN_OLLAMA_SYNTHESIZER_MODEL` | `qwen3.5:latest` |
| `SOVEREIGN_OLLAMA_ARCHIVIST_MODEL` | `gemma4:e4b` |
| `SOVEREIGN_MAX_CONCURRENT_WORKERS` | `2` |
| `SOVEREIGN_PROVIDER_TIMEOUT_SECONDS` | `20` |

The adapter calls local Ollama through LiteLLM and normalizes responses into the existing provider result model. `system_status` probes `/api/tags` with a bounded timeout and returns `ollama_available`, `ollama_api_base`, and the installed `ollama_models`; an unavailable service produces `false` and an empty list rather than failing the tool.

Other supported names include `SOVEREIGN_CONFIG_PATH`, `SOVEREIGN_DATA_DIR`, and `SOVEREIGN_LOG_LEVEL`. See `config/council.example.yaml` for limits, retries, memory extraction, and worker concurrency. Tested local models: `qwen2.5-coder:7b`, `qwen3.5:latest`, `deepseek-r1:latest`, `gemma4:e4b`, and `gpt-oss:latest`.
