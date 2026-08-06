# Council Architecture

## Overview

The Sovereign Exoself Council is a bounded multi-agent orchestration system running locally on Ollama. It routes tasks through a pipeline of specialized roles, each backed by a lightweight model optimized for that role.

## Model Assignment (Config B — Benchmark Winner)

| Role | Model | Rationale |
|------|-------|-----------|
| Manager | granite3.3:2b | Fast routing decisions, 1504ms avg |
| Worker | qwen2.5-coder:7b | Quality code execution, 4.7GB VRAM |
| Critic | qwen2.5-coder:7b | Reliable code review, shared weights |
| Synthesizer | granite3.3:2b | Fast result merging |
| Archivist | granite3.3:2b | Fast memory extraction |

Total VRAM: ~6.2GB (fits RTX 4060 OC 8GB with headroom).

## Routing Flow

```
                    ┌─────────────┐
                    │   Manager   │
                    │ (granite3.3)│
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
          ┌──────┐    ┌──────┐    ┌──────┐
          │ FAST │    │REVIEW│    │ FULL │
          └──┬───┘    └──┬───┘    └──┬───┘
             │           │           │
             ▼           ▼           ▼
         ┌──────┐    ┌──────┐    ┌──────┐
         │Worker│    │Worker│    │Worker│
         └──┬───┘    └──┬───┘    └──┬───┘
            │           │           │
            │           ▼           │
            │       ┌──────┐        │
            │       │Critic│        │
            │       └──┬───┘        │
            │          │            │
            │     ┌────┴────┐       │
            │     │         │       │
            │   APPROVE   REJECT    │
            │     │         │       │
            │     │    ┌────┘       │
            │     │    │ retry      │
            │     ▼    ▼            │
            │  ┌──────────┐         │
            │  │Synthesizer│        │
            │  └──────────┘         │
            │                       │
            └───────────┬───────────┘
                        │
                        ▼
                   ┌──────────┐
                   │Archivist │
                   └──────────┘
```

### Route Selection

The manager returns a `ManagerDecision` with:
- `route`: "fast" | "review" | "full"
- `risk`: "low" | "medium" | "high"
- `worker_profile`: which specialization to use

**FAST path** (default): Manager → Worker → Result
- Used for: simple questions, facts, quick analysis
- No quality verification
- Lowest latency (~1.5s)

**REVIEW path**: Manager → Worker → Critic → Synthesizer → Result
- Used for: code changes, architecture decisions, when quality matters
- Critic can REJECT and trigger retry (max 1 round by default)
- Medium latency (~3s)

**FULL path**: Manager → Worker → Critic → Synthesizer → Archivist → Result
- Used for: complex tasks requiring memory extraction
- Full pipeline with archival
- Highest latency (~4s)

## Worker Profiles

Workers can be specialized via profiles loaded from `prompts/profiles/*.txt`:

| Profile | Purpose |
|---------|---------|
| code_engineer | Code implementation, debugging, refactoring |
| system_engineer | Infrastructure, DevOps, system design |
| researcher | Information gathering, analysis |
| technical_writer | Documentation, prose |
| planner | Task decomposition, project planning |
| general_operator | Default fallback |

## Constraints

- **Sequential execution**: max_concurrent_workers=1 (8GB VRAM constraint)
- **Temperature**: 0.0 (deterministic output)
- **Thinking**: disabled (reduces latency)
- **Max review rounds**: 1 (prevents infinite retry loops)
- **Max council rounds**: 2 (prevents cascading failures)
- **Provider timeout**: 120s (prevents hung requests)
- **Retry limit**: 2 (transient error recovery)

## Observability

`system_status` returns:
- `prompt_versions`: version of each role prompt
- `model_mapping`: which model serves each role
- `active_runs`: current concurrent executions
- `metrics`: per-run timing, token counts, parse retries

Each `council_run` response includes:
- `route`: which path was taken
- `models`: which model served each role
- `metrics`: duration_ms, input_tokens, output_tokens, model_calls, parse_retries