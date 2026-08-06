# Migration Guide

## From Previous Version

### Changes in 2.0.0

1. **New routing system**: Council now uses fast/review/full paths instead of running all agents for every task.

2. **Model assignment**: Config B uses granite3.3:2b for manager/synthesizer/archivist and qwen2.5-coder:7b for worker/critic.

3. **Sequential execution**: max_concurrent_workers defaults to 1 for 8GB VRAM systems.

4. **New parameters**: `council_run` now accepts `worker_profile`, `needs_memory`, `max_rounds`, and route override via `mode`.

5. **Prompt versioning**: All prompts are now versioned and tracked via `system_status`.

### Breaking Changes

- `council_run` response now includes `route`, `models`, and `metrics` fields
- `system_status` response now includes `prompt_versions`, `model_mapping`, `active_runs`
- Manager now returns structured JSON instead of free-form text
- Worker profiles are now loaded from files instead of hardcoded

### Migration Steps

1. Update environment variables:
   ```bash
   # Add new settings
   SOVEREIGN_MAX_CONCURRENT_WORKERS=1
   SOVEREIGN_DEFAULT_ROUTE=auto
   SOVEREIGN_TEMPERATURE=0.0
   SOVEREIGN_THINK=false
   ```

2. Pull new models:
   ```bash
   ollama pull granite3.3:2b
   ollama pull qwen2.5-coder:7b
   ```

3. Update client code to handle new response fields:
   ```python
   result = await session.call_tool("council_run", {"task": "..."})
   payload = json.loads(result.content[0].text)
   # New fields available:
   print(payload["route"])      # "fast", "review", or "full"
   print(payload["models"])     # {"worker": "qwen2.5-coder:7b", ...}
   print(payload["metrics"])    # {"duration_ms": 1504, ...}
   ```

4. Run tests to verify:
   ```bash
   python -m pytest tests/ -v
   ```

### Rollback

To revert to previous behavior:

1. Set `SOVEREIGN_PROVIDER_MODE=mock` (or remove ollama config)
2. Remove new environment variables
3. Revert code changes

The system will fall back to default behavior with mock provider.

### Adding Worker Profiles

1. Create profile file:
   ```bash
   echo "## Custom Profile\nYou are a..." > src/sovereign_exoself_mcp/prompts/profiles/custom.txt
   ```

2. Add to PROFILES list in `prompts.py`:
   ```python
   PROFILES = [
       ...,
       "custom",
   ]
   ```

3. Use in requests:
   ```python
   await session.call_tool("council_run", {
       "task": "...",
       "worker_profile": "custom"
   })
   ```

### Troubleshooting

**Issue**: Model not found
```bash
# Pull the required models
ollama pull granite3.3:2b
ollama pull qwen2.5-coder:7b
```

**Issue**: Timeout errors
```bash
# Increase timeout
export SOVEREIGN_PROVIDER_TIMEOUT_SECONDS=180
```

**Issue**: JSON parse errors
```bash
# Check model supports JSON output
ollama show granite3.3:2b
```

**Issue**: High latency
```bash
# Disable thinking mode
export SOVEREIGN_THINK=false
# Reduce context window
export SOVEREIGN_CONTEXT_WORKER=4096
```
