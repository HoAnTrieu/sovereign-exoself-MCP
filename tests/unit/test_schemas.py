import pytest

from sovereign_exoself_mcp.domain import (
    CouncilRequest,
    ExpectedOutput,
    ManagerDecision,
    RiskLevel,
    Route,
    TaskType,
    WorkerProfile,
)


class TestManagerDecisionSchema:
    def test_valid_decision_parses(self):
        data = {
            "task_type": "coding",
            "route": "fast",
            "risk": "low",
            "worker_profile": "code_engineer",
            "objective": "Fix the bug",
            "constraints": [],
            "required_tools": [],
            "expected_output": "code",
            "needs_memory": False,
        }
        decision = ManagerDecision(**data)
        assert decision.route == Route.FAST
        assert decision.task_type == TaskType.CODING

    def test_all_task_types_accepted(self):
        for tt in TaskType:
            data = {
                "task_type": tt,
                "route": "fast",
                "risk": "low",
                "worker_profile": "general_operator",
                "objective": "Test",
                "constraints": [],
                "required_tools": [],
                "expected_output": "answer",
                "needs_memory": False,
            }
            decision = ManagerDecision(**data)
            assert decision.task_type == tt

    def test_all_routes_accepted(self):
        for route in Route:
            data = {
                "task_type": "general",
                "route": route,
                "risk": "low",
                "worker_profile": "general_operator",
                "objective": "Test",
                "constraints": [],
                "required_tools": [],
                "expected_output": "answer",
                "needs_memory": False,
            }
            decision = ManagerDecision(**data)
            assert decision.route == route

    def test_all_worker_profiles_accepted(self):
        for profile in WorkerProfile:
            data = {
                "task_type": "general",
                "route": "fast",
                "risk": "low",
                "worker_profile": profile,
                "objective": "Test",
                "constraints": [],
                "required_tools": [],
                "expected_output": "answer",
                "needs_memory": False,
            }
            decision = ManagerDecision(**data)
            assert decision.worker_profile == profile

    def test_constraints_limited_to_6(self):
        data = {
            "task_type": "coding",
            "route": "fast",
            "risk": "low",
            "worker_profile": "code_engineer",
            "objective": "Test",
            "constraints": tuple(f"c{i}" for i in range(7)),
            "required_tools": [],
            "expected_output": "code",
            "needs_memory": False,
        }
        with pytest.raises(Exception):
            ManagerDecision(**data)

    def test_required_tools_limited_to_5(self):
        data = {
            "task_type": "coding",
            "route": "fast",
            "risk": "low",
            "worker_profile": "code_engineer",
            "objective": "Test",
            "constraints": [],
            "required_tools": tuple(f"t{i}" for i in range(6)),
            "expected_output": "code",
            "needs_memory": False,
        }
        with pytest.raises(Exception):
            ManagerDecision(**data)

    def test_objective_max_length_500(self):
        data = {
            "task_type": "coding",
            "route": "fast",
            "risk": "low",
            "worker_profile": "code_engineer",
            "objective": "x" * 501,
            "constraints": [],
            "required_tools": [],
            "expected_output": "code",
            "needs_memory": False,
        }
        with pytest.raises(Exception):
            ManagerDecision(**data)


class TestCriticVerdictSchema:
    def test_approve_verdict(self):
        from sovereign_exoself_mcp.domain import CriticVerdict, Verdict

        data = {
            "verdict": "APPROVE",
            "confidence": 0.95,
            "issues": [],
            "required_fixes": [],
            "verification": ["All tests pass"],
        }
        verdict = CriticVerdict(**data)
        assert verdict.verdict == Verdict.APPROVE

    def test_reject_verdict_with_issues(self):
        from sovereign_exoself_mcp.domain import CriticIssue, CriticVerdict, Verdict

        data = {
            "verdict": "REJECT",
            "confidence": 0.96,
            "issues": [
                {
                    "severity": "high",
                    "location": "src/provider.py",
                    "problem": "Timeout not propagated",
                    "fix": "Pass timeout to constructor",
                }
            ],
            "required_fixes": ["Add regression test"],
            "verification": [],
        }
        verdict = CriticVerdict(**data)
        assert verdict.verdict == Verdict.REJECT
        assert len(verdict.issues) == 1
        assert verdict.issues[0].severity == "high"

    def test_issues_limited_to_5(self):
        from sovereign_exoself_mcp.domain import CriticVerdict

        data = {
            "verdict": "REJECT",
            "confidence": 0.9,
            "issues": [
                {
                    "severity": "low",
                    "location": f"file{i}.py",
                    "problem": f"Issue {i}",
                    "fix": f"Fix {i}",
                }
                for i in range(6)
            ],
            "required_fixes": [],
            "verification": [],
        }
        with pytest.raises(Exception):
            CriticVerdict(**data)

    def test_confidence_bounds(self):
        from sovereign_exoself_mcp.domain import CriticVerdict

        data = {
            "verdict": "APPROVE",
            "confidence": 1.5,
            "issues": [],
            "required_fixes": [],
            "verification": [],
        }
        with pytest.raises(Exception):
            CriticVerdict(**data)


class TestSynthesisOutputSchema:
    def test_completed_status(self):
        from sovereign_exoself_mcp.domain import SynthesisOutput, SynthesisStatus

        data = {
            "status": "completed",
            "summary": "Task done",
            "result": {},
            "files_changed": [],
            "verification": [],
            "warnings": [],
            "next_action": None,
        }
        output = SynthesisOutput(**data)
        assert output.status == SynthesisStatus.COMPLETED

    def test_all_statuses_accepted(self):
        from sovereign_exoself_mcp.domain import SynthesisOutput, SynthesisStatus

        for status in SynthesisStatus:
            data = {
                "status": status,
                "summary": "Test",
            }
            output = SynthesisOutput(**data)
            assert output.status == status


class TestCouncilRequestSchema:
    def test_valid_request(self):
        request = CouncilRequest(task="Fix the bug")
        assert request.mode.value == "auto"
        assert request.route_override is None

    def test_route_override(self):
        request = CouncilRequest(task="Fix the bug", route_override=Route.REVIEW)
        assert request.route_override == Route.REVIEW

    def test_task_max_length(self):
        with pytest.raises(Exception):
            CouncilRequest(task="x" * 8001)

    def test_empty_task_rejected(self):
        with pytest.raises(Exception):
            CouncilRequest(task="")
