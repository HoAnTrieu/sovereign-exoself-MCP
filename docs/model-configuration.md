# Model Configuration

## Config B — Benchmark Winner

```yaml
models:
  manager: granite3.3:2b        # 1.5GB VRAM, fast routing
  worker: qwen2.5-coder:7b      # 4.7GB VRAM, quality execution
  critic: qwen2.5-coder:7b      # 4.7GB VRAM, shared weights with worker
  synthesizer: granite3.3:2b    # 1.5GB VRAM, shared instance with manager
  archivist: granite3.3:2b      # 1.5GB VRAM, shared instance with manager
```

Total VRAM: ~6.2GB (fits RTX 4060 OC 8GB with headroom).

## Benchmark Results

| Metric | Value |
|--------|-------|
| Average time | 1504 ms |
| P95 time | 3428 ms |
| Average tokens | 87 |
| Average TPS | 64.6 |
| Timeouts | 0 |
| JSON errors | 0 |
| Success rate | 100% |

## Environment Variables

All settings are configurable via environment variables with `SOVEREIGN_` prefix:

```bash
SOVEREIGN_PROVIDER_MODE=ollama
SOVEREIGN_OLLAMA_API_BASE=http://127.0.0.1:11434
SOVEREIGN_OLLAMA_MANAGER_MODEL=granite3.3:2b
SOVEREIGN_OLLAMA_WORKER_MODEL=qwen2.5-coder:7b
SOVEREIGN_OLLAMA_CRITIC_MODEL=qwen2.5-coder:7b
SOVEREIGN_OLLAMA_SYNTHESIZER_MODEL=granite3.3:2b
SOVEREIGN_OLLAMA_ARCHIVIST_MODEL=granite3.3:2b
```

## Context Window Budgets

```yaml
context:
  manager: 4096
  worker: 8192
  critic: 8192
  synthesizer: 4096
  archivist: 4096
```

## Generation Parameters

```yaml
temperature: 0.0    # Deterministic output
think: false        # No thinking mode (reduces latency)
```

## Changing Models

### Using Environment Variables
```bash
export SOVEREIGN_OLLAMA_WORKER_MODEL=qwen3:8b
export SOVEREIGN_OLLAMA_MANAGER_MODEL=gemma2:2b
```

### Using config/council.yaml
```yaml
ollama_worker_model: qwen3:8b
ollama_manager_model: gemma2:2b
```

### Model Requirements
- Manager, synthesizer, archivist: fast models (2-3B parameters)
- Worker, critic: quality models (7B parameters)
- All models must support JSON output
- Temperature 0 recommended for deterministic results

## Model Sharing

Models are reused across roles when possible:
- granite3.3:2b serves manager + synthesizer + archivist
- qwen2.5-coder:7b serves worker + critic

Ollama handles model loading/unloading automatically. The `keep_alive` setting controls how long models stay in memory.
