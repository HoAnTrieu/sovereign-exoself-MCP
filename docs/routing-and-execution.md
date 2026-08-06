# Routing and Execution

## Overview

The council routes tasks through three paths based on complexity, risk, and verification needs.

## Route Selection

The manager analyzes each task and returns a `ManagerDecision` with:
- `route`: fast, review, or full
- `risk`: low, medium, or high
- `worker_profile`: which specialization to use

### Fast Path (Default)
```
Manager → Worker → Result
```
- Used for: simple questions, facts, quick analysis
- No quality verification
- Lowest latency (~1.5s)
- 2 model calls (manager + worker)

### Review Path
```
Manager → Worker → Critic → Synthesizer → Result
```
- Used for: code changes, architecture decisions, when quality matters
- Critic can REJECT and trigger retry (max 1 round by default)
- Medium latency (~3s)
- 3-4 model calls

### Full Council Path
```
Manager → Worker → Critic → Synthesizer → Archivist → Result
```
- Used for: complex tasks requiring memory extraction
- Full pipeline with archival
- Highest latency (~4s)
- 4-5 model calls

## Route Override

The `council_run` tool accepts a `mode` parameter that can override the manager's route decision:

```json
{
  "task": "Complex architecture task",
  "mode": "fast"
}
```

Valid values: `auto` (manager decides), `fast`, `review`, `full`

## Execution Constraints

- **Sequential execution**: max_concurrent_workers=1 (8GB VRAM constraint)
- **No parallel agents**: worker and critic never run simultaneously
- **Parse retry**: max 1 retry on JSON format error with format-fix prompt
- **Critic retry**: max 1 round on REJECT (configurable via max_review_rounds)
- **Graceful fallback**: if critic/synthesizer fails, returns worker result as partial

## Memory Flow

Memory is only extracted when:
1. `needs_memory=true` in the request, OR
2. Manager sets `needs_memory=true` based on task analysis

The archivist only runs in the FULL path. Fast and REVIEW paths skip archival.

## Metrics

Each run returns metrics:
```json
{
  "duration_ms": 1504,
  "input_tokens": 100,
  "output_tokens": 87,
  "model_calls": 3,
  "parse_retries": 0
}
```

- `model_calls`: number of LLM API calls made
- `parse_retries`: number of format-fix retries
- `duration_ms`: total wall-clock time
