import pytest

from sovereign_exoself_mcp.prompts import (
    PROMPT_VERSIONS,
    PROFILES,
    build_system_prompt,
    get_all_versions,
    get_prompt_version,
    load_profile,
    load_prompt,
)


class TestPromptExistence:
    def test_all_role_prompts_exist(self):
        for name in ("common", "manager", "worker", "critic", "synthesizer", "archivist"):
            content = load_prompt(name)
            assert len(content) > 0, f"Prompt {name} is empty"

    def test_all_profiles_exist(self):
        for profile in PROFILES:
            content = load_profile(profile)
            assert len(content) > 0, f"Profile {profile} is empty"

    def test_build_system_prompt_for_all_roles(self):
        for role in ("manager", "worker", "critic", "synthesizer", "archivist"):
            prompt = build_system_prompt(role)
            assert len(prompt) > 100, f"System prompt for {role} too short"

    def test_build_system_prompt_with_profiles(self):
        for profile in PROFILES:
            prompt = build_system_prompt("worker", profile)
            assert profile.replace("_", " ") in prompt.lower() or len(prompt) > 500


class TestPromptVersioning:
    def test_all_prompts_have_version(self):
        versions = get_all_versions()
        for name in ("common", "manager", "worker", "critic", "synthesizer", "archivist"):
            assert name in versions, f"Missing version for {name}"
            assert versions[name].startswith("2."), f"Unexpected version for {name}: {versions[name]}"

    def test_prompt_meta_has_required_fields(self):
        for name, meta in PROMPT_VERSIONS.items():
            assert meta.name == name
            assert meta.version
            assert meta.model_family
            assert meta.purpose
            assert meta.output_schema

    def test_get_prompt_version_returns_string(self):
        assert isinstance(get_prompt_version("manager"), str)
        assert get_prompt_version("nonexistent") == "unknown"


class TestPromptContent:
    def test_common_prompt_prohibits_chain_of_thought(self):
        common = load_prompt("common")
        assert "chain-of-thought" in common.lower()
        assert "hidden reasoning" in common.lower()

    def test_common_prompt_prohibits_markdown_for_json(self):
        common = load_prompt("common")
        assert "markdown" in common.lower() or "code fence" in common.lower()

    def test_common_prompt_prohibits_false_claims(self):
        common = load_prompt("common")
        assert "invent" in common.lower() or "fabricate" in common.lower()

    def test_manager_prompt_has_output_schema(self):
        manager = load_prompt("manager")
        assert "task_type" in manager
        assert "route" in manager
        assert "worker_profile" in manager

    def test_manager_prompt_has_route_rules(self):
        manager = load_prompt("manager")
        assert "fast" in manager.lower()
        assert "review" in manager.lower()
        assert "full" in manager.lower()

    def test_manager_prompt_has_task_types(self):
        manager = load_prompt("manager")
        for task_type in ("coding", "debugging", "architecture", "research", "documentation"):
            assert task_type in manager.lower()

    def test_worker_prompt_has_profiles(self):
        worker = load_prompt("worker")
        for profile in PROFILES:
            assert profile in worker

    def test_critic_prompt_has_verdict_schema(self):
        critic = load_prompt("critic")
        assert "APPROVE" in critic
        assert "REJECT" in critic
        assert "confidence" in critic

    def test_synthesizer_prompt_has_status_values(self):
        synthesizer = load_prompt("synthesizer")
        for status in ("completed", "partial", "blocked", "failed"):
            assert status in synthesizer.lower()

    def test_archivist_prompt_has_action_values(self):
        archivist = load_prompt("archivist")
        for action in ("none", "insert", "update", "upsert", "delete"):
            assert action in archivist.lower()

    def test_no_prompt_exceeds_reasonable_size(self):
        for name in ("common", "manager", "worker", "critic", "synthesizer", "archivist"):
            prompt = load_prompt(name)
            assert len(prompt) < 5000, f"Prompt {name} too large: {len(prompt)} chars"
