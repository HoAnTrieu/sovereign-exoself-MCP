# Council Prompts

## Overview

Each council role has a dedicated prompt file loaded from `src/sovereign_exoself_mcp/prompts/`. All prompts share a common prefix loaded from `common.txt`.

## Prompt Files

| File | Role | Model | Version |
|------|------|-------|---------|
| `common.txt` | All roles | — | 2.0.0 |
| `manager.txt` | Manager | granite3.3:2b | 2.0.0 |
| `worker.txt` | Worker | qwen2.5-coder:7b | 2.0.0 |
| `critic.txt` | Critic | qwen2.5-coder:7b | 2.0.0 |
| `synthesizer.txt` | Synthesizer | granite3.3:2b | 2.0.0 |
| `archivist.txt` | Archivist | granite3.3:2b | 2.0.0 |

## Worker Profiles

| Profile | File | Purpose |
|---------|------|---------|
| code_engineer | `profiles/code_engineer.txt` | Code implementation, debugging, refactoring |
| system_engineer | `profiles/system_engineer.txt` | Infrastructure, DevOps, system design |
| researcher | `profiles/researcher.txt` | Information gathering, analysis |
| technical_writer | `profiles/technical_writer.txt` | Documentation, prose |
| planner | `profiles/planner.txt` | Task decomposition, project planning |
| general_operator | `profiles/general_operator.txt` | Default fallback |

## Common Instructions

All roles receive these instructions via `common.txt`:

- Return only the information required by your role
- Do not reveal private chain-of-thought
- Do not invent facts, files, commands, or successful actions
- Prefer deterministic, concise, machine-parseable output
- Follow the output schema exactly
- If the output schema requires JSON, return raw JSON only
- Do not wrap JSON in markdown code fences
- Do not expand scope beyond the assigned role
- If information is missing, return a status field indicating the gap instead of guessing

## Output Schemas

### Manager Decision
```json
{
  "task_type": "coding",
  "route": "fast",
  "risk": "low",
  "worker_profile": "code_engineer",
  "objective": "Clear description of what needs to be done",
  "constraints": ["constraint1", "constraint2"],
  "required_tools": [],
  "expected_output": "code",
  "needs_memory": false
}
```

### Critic Verdict
```json
{
  "verdict": "APPROVE",
  "confidence": 0.93,
  "issues": [],
  "required_fixes": [],
  "verification": ["All tests pass"]
}
```

### Synthesis Output
```json
{
  "status": "completed",
  "summary": "Brief summary",
  "result": {},
  "files_changed": ["file1.py"],
  "verification": ["pytest passed"],
  "warnings": [],
  "next_action": null
}
```

### Archivist Output
```json
{
  "action": "upsert",
  "memories": [
    {
      "category": "system_configuration",
      "key": "memory_key",
      "value": {},
      "reason": "Why this is worth storing",
      "confidence": 1.0
    }
  ]
}
```

## Versioning

Each prompt has metadata tracked in `prompts.py`:

```python
PROMPT_VERSIONS = {
    "common": PromptMeta("common", "2.0.0", "all", "shared_instructions", "none"),
    "manager": PromptMeta("manager", "2.0.0", "granite", "council_routing", "manager_decision_v1"),
    ...
}
```

Versions are exposed via `system_status` tool response under `prompt_versions`.

## Adding New Profiles

1. Create `src/sovereign_exoself_mcp/prompts/profiles/<name>.txt`
2. Add the profile name to `PROFILES` list in `prompts.py`
3. Write tests in `tests/unit/test_prompts.py`
4. Bump the worker prompt version if the profile changes task execution behavior
