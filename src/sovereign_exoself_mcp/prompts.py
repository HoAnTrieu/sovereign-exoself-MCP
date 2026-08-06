"""Prompt loader for council roles."""

from pathlib import Path
from dataclasses import dataclass

PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass(frozen=True, slots=True)
class PromptMeta:
    name: str
    version: str
    model_family: str
    purpose: str
    output_schema: str


PROMPT_VERSIONS = {
    "common": PromptMeta("common", "2.0.0", "all", "shared_instructions", "none"),
    "manager": PromptMeta("manager", "2.0.0", "granite", "council_routing", "manager_decision_v1"),
    "worker": PromptMeta("worker", "2.0.0", "qwen", "task_execution", "worker_result_v1"),
    "critic": PromptMeta("critic", "2.0.0", "qwen", "quality_review", "critic_verdict_v1"),
    "synthesizer": PromptMeta("synthesizer", "2.0.0", "granite", "result_synthesis", "synthesis_output_v1"),
    "archivist": PromptMeta("archivist", "2.0.0", "granite", "memory_extraction", "memory_action_v1"),
}

PROFILES = [
    "code_engineer",
    "system_engineer",
    "researcher",
    "technical_writer",
    "planner",
    "general_operator",
]


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text().strip()


def load_profile(name: str) -> str:
    path = PROMPTS_DIR / "profiles" / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    return path.read_text().strip()


ROLE_MAP = {
    "manager": "manager",
    "worker": "worker",
    "engineer": "worker",
    "analyst": "worker",
    "critic": "critic",
    "synthesizer": "synthesizer",
    "archivist": "archivist",
}


def build_system_prompt(role: str, profile: str | None = None) -> str:
    common = load_prompt("common")
    prompt_name = ROLE_MAP.get(role, role)
    role_prompt = load_prompt(prompt_name)

    parts = [common, "", role_prompt]

    if profile and role in ("worker", "engineer", "analyst"):
        profile_prompt = load_profile(profile)
        parts.extend(["", profile_prompt])

    return "\n".join(parts)


def get_prompt_version(name: str) -> str:
    meta = PROMPT_VERSIONS.get(name)
    return meta.version if meta else "unknown"


def get_all_versions() -> dict[str, str]:
    return {name: meta.version for name, meta in PROMPT_VERSIONS.items()}