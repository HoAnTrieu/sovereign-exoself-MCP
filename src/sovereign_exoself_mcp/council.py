"""Deterministic council orchestration with routing."""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import uuid4

import anyio

from sovereign_exoself_mcp.domain import (
    Budget,
    CouncilMetrics,
    CouncilRequest,
    CouncilResult,
    CriticVerdict,
    ManagerDecision,
    MemoryKind,
    MemoryRecord,
    Route,
    SynthesisOutput,
    Verdict,
)
from sovereign_exoself_mcp.memory import MemoryRepository
from sovereign_exoself_mcp.providers import Provider, ProviderError, retry_completion
from sovereign_exoself_mcp.security import contains_secret
from sovereign_exoself_mcp.settings import Settings

_TOKEN_LIMITS = {Budget.LOW: 600, Budget.BALANCED: 1200, Budget.DEEP: 2400}


def _parse_json_response(content: str) -> dict | None:
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
    return None


@dataclass(slots=True)
class Council:
    settings: Settings
    memory: MemoryRepository
    provider: Provider

    async def run(self, request: CouncilRequest) -> CouncilResult:
        run_id = uuid4()
        start_ms = int(anyio.current_time() * 1000)
        memories = await self.memory.search(request.task, self.settings.memory_limit)
        total_input = 0
        total_output = 0
        model_calls = 0
        parse_retries = 0
        warnings: list[str] = []
        models_used: dict[str, str] = {}

        try:
            manager_decision = await self._manager_call(request, memories)
            model_calls += 1
            total_input += 100
            total_output += 50
        except ProviderError as error:
            answer = "Council manager is unavailable. Review provider configuration and retry."
            await self.memory.commit_run(str(run_id), request.session_id, "error", answer)
            return CouncilResult(
                status="error",
                run_id=run_id,
                route=Route.FAST,
                models={},
                result=answer,
                metrics=CouncilMetrics(
                    duration_ms=int(anyio.current_time() * 1000) - start_ms,
                    input_tokens=0,
                    output_tokens=0,
                    model_calls=0,
                    parse_retries=0,
                ),
                memory_updates=0,
                warnings=(f"manager unavailable: {error.message}",),
            )

        route = request.route_override or manager_decision.route
        needs_memory = request.needs_memory if request.needs_memory is not None else manager_decision.needs_memory
        profile = request.worker_profile or manager_decision.worker_profile

        if route == Route.FAST:
            result = await self._fast_path(
                request, manager_decision, profile, memories,
                run_id, start_ms, total_input, total_output, model_calls, parse_retries, warnings, models_used
            )
        elif route == Route.REVIEW:
            result = await self._review_path(
                request, manager_decision, profile, memories,
                run_id, start_ms, total_input, total_output, model_calls, parse_retries, warnings, models_used
            )
        else:
            result = await self._full_path(
                request, manager_decision, profile, memories,
                run_id, start_ms, total_input, total_output, model_calls, parse_retries, warnings, models_used, needs_memory
            )

        return result

    async def _manager_call(
        self, request: CouncilRequest, memories: Sequence[MemoryRecord]
    ) -> ManagerDecision:
        memory_context = "\n".join(record.content[:200] for record in memories[:2])
        prompt = f"Task: {request.task}"
        if memory_context:
            prompt += f"\nRelevant memory: {memory_context}"

        result = await retry_completion(
            self.provider, "manager", prompt, _TOKEN_LIMITS[Budget.LOW],
            self.settings.retry_limit, profile=None
        )

        parsed = _parse_json_response(result.content)
        if parsed is not None:
            try:
                return ManagerDecision(**parsed)
            except Exception:
                pass

        fix_prompt = (
            "Your previous output was not valid JSON. "
            "Return ONLY the JSON object matching the ManagerDecision schema. "
            "No markdown, no code fences, no commentary.\n\n"
            f"Original task: {request.task}"
        )
        try:
            retry = await retry_completion(
                self.provider, "manager", fix_prompt, _TOKEN_LIMITS[Budget.LOW],
                0, profile=None
            )
            parsed = _parse_json_response(retry.content)
            if parsed is not None:
                try:
                    return ManagerDecision(**parsed)
                except Exception:
                    pass
        except ProviderError:
            pass

        return ManagerDecision(
            task_type="general",
            route=Route.FAST,
            risk="low",
            worker_profile="general_operator",
            objective=request.task,
            expected_output="answer",
            needs_memory=False,
        )

    async def _fast_path(
        self, request, manager_decision, profile, memories,
        run_id, start_ms, total_input, total_output, model_calls, parse_retries, warnings, models_used
    ) -> CouncilResult:
        memory_context = "\n".join(record.content[:500] for record in memories)
        prompt = f"Task: {manager_decision.objective}"
        if memory_context:
            prompt += f"\nContext: {memory_context}"
        if manager_decision.constraints:
            prompt += f"\nConstraints: {', '.join(manager_decision.constraints)}"

        try:
            worker_result = await retry_completion(
                self.provider, "worker", prompt, _TOKEN_LIMITS[Budget.LOW],
                self.settings.retry_limit, profile=profile.value
            )
            model_calls += 1
            total_input += worker_result.input_tokens
            total_output += worker_result.output_tokens
            models_used["worker"] = worker_result.model
        except ProviderError as error:
            warnings.append(f"worker unavailable: {error.message}")
            end_ms = int(anyio.current_time() * 1000)
            return CouncilResult(
                status="error",
                run_id=run_id,
                route=Route.FAST,
                models=models_used,
                result=None,
                metrics=CouncilMetrics(
                    duration_ms=end_ms - start_ms,
                    input_tokens=total_input,
                    output_tokens=total_output,
                    model_calls=model_calls,
                    parse_retries=parse_retries,
                ),
                memory_updates=0,
                warnings=tuple(warnings),
            )

        status = "ok" if not warnings else "partial"
        await self.memory.commit_run(str(run_id), request.session_id, status, worker_result.content)
        end_ms = int(anyio.current_time() * 1000)
        return CouncilResult(
            status=status,
            run_id=run_id,
            route=Route.FAST,
            models=models_used,
            result=worker_result.content,
            metrics=CouncilMetrics(
                duration_ms=end_ms - start_ms,
                input_tokens=total_input,
                output_tokens=total_output,
                model_calls=model_calls,
                parse_retries=parse_retries,
            ),
            memory_updates=0,
            warnings=tuple(warnings),
        )

    async def _review_path(
        self, request, manager_decision, profile, memories,
        run_id, start_ms, total_input, total_output, model_calls, parse_retries, warnings, models_used
    ) -> CouncilResult:
        memory_context = "\n".join(record.content[:500] for record in memories)
        prompt = f"Task: {manager_decision.objective}"
        if memory_context:
            prompt += f"\nContext: {memory_context}"
        if manager_decision.constraints:
            prompt += f"\nConstraints: {', '.join(manager_decision.constraints)}"

        try:
            worker_result = await retry_completion(
                self.provider, "worker", prompt, _TOKEN_LIMITS[Budget.LOW],
                self.settings.retry_limit, profile=profile.value
            )
            model_calls += 1
            total_input += worker_result.input_tokens
            total_output += worker_result.output_tokens
            models_used["worker"] = worker_result.model
        except ProviderError as error:
            warnings.append(f"worker unavailable: {error.message}")
            end_ms = int(anyio.current_time() * 1000)
            return CouncilResult(
                status="error",
                run_id=run_id,
                route=Route.REVIEW,
                models=models_used,
                result=None,
                metrics=CouncilMetrics(
                    duration_ms=end_ms - start_ms,
                    input_tokens=total_input,
                    output_tokens=total_output,
                    model_calls=model_calls,
                    parse_retries=parse_retries,
                ),
                memory_updates=0,
                warnings=tuple(warnings),
            )

        critic_prompt = f"Original task: {manager_decision.objective}\n\nWorker response:\n{worker_result.content}"
        try:
            critic_result = await retry_completion(
                self.provider, "critic", critic_prompt, _TOKEN_LIMITS[Budget.LOW],
                self.settings.retry_limit, profile=None
            )
            model_calls += 1
            total_input += critic_result.input_tokens
            total_output += critic_result.output_tokens
            models_used["critic"] = critic_result.model
        except ProviderError as error:
            warnings.append(f"critic unavailable: {error.message}")
            end_ms = int(anyio.current_time() * 1000)
            return CouncilResult(
                status="partial",
                run_id=run_id,
                route=Route.REVIEW,
                models=models_used,
                result=worker_result.content,
                metrics=CouncilMetrics(
                    duration_ms=end_ms - start_ms,
                    input_tokens=total_input,
                    output_tokens=total_output,
                    model_calls=model_calls,
                    parse_retries=parse_retries,
                ),
                memory_updates=0,
                warnings=tuple(warnings),
            )

        verdict_data = _parse_json_response(critic_result.content)
        verdict = None
        if verdict_data:
            try:
                verdict = CriticVerdict(**verdict_data)
            except Exception:
                pass

        if verdict is None:
            fix_prompt = (
                "Your previous output was not valid JSON for CriticVerdict schema. "
                "Return ONLY the JSON object. No markdown, no code fences, no commentary.\n\n"
                f"Original task: {manager_decision.objective}\n"
                f"Worker response: {worker_result.content}"
            )
            try:
                retry = await retry_completion(
                    self.provider, "critic", fix_prompt, _TOKEN_LIMITS[Budget.LOW],
                    0, profile=None
                )
                parsed = _parse_json_response(retry.content)
                if parsed:
                    try:
                        verdict = CriticVerdict(**parsed)
                    except Exception:
                        pass
            except ProviderError:
                pass

        if verdict and verdict.verdict == Verdict.REJECT:
            max_rounds = self.settings.max_review_rounds
            for round_num in range(max_rounds):
                parse_retries += 1
                retry_prompt = f"Previous attempt was rejected.\nIssues: {[i.problem for i in verdict.issues]}\n\nPlease fix these issues and return corrected result."
                try:
                    worker_result = await retry_completion(
                        self.provider, "worker", retry_prompt, _TOKEN_LIMITS[Budget.LOW],
                        self.settings.retry_limit, profile=profile.value
                    )
                    model_calls += 1
                    total_input += worker_result.input_tokens
                    total_output += worker_result.output_tokens
                except ProviderError:
                    break

        synthesis_prompt = f"Task: {manager_decision.objective}\n\nWorker: {worker_result.content}\n\nCritic: {critic_result.content}"
        try:
            synthesis_result = await retry_completion(
                self.provider, "synthesizer", synthesis_prompt, _TOKEN_LIMITS[Budget.LOW],
                self.settings.retry_limit, profile=None
            )
            model_calls += 1
            total_input += synthesis_result.input_tokens
            total_output += synthesis_result.output_tokens
            models_used["synthesizer"] = synthesis_result.model
            final_result = synthesis_result.content
        except ProviderError:
            final_result = worker_result.content

        status = "ok" if not warnings else "partial"
        await self.memory.commit_run(str(run_id), request.session_id, status, final_result)
        end_ms = int(anyio.current_time() * 1000)
        return CouncilResult(
            status=status,
            run_id=run_id,
            route=Route.REVIEW,
            models=models_used,
            result=final_result,
            metrics=CouncilMetrics(
                duration_ms=end_ms - start_ms,
                input_tokens=total_input,
                output_tokens=total_output,
                model_calls=model_calls,
                parse_retries=parse_retries,
            ),
            memory_updates=0,
            warnings=tuple(warnings),
        )

    async def _full_path(
        self, request, manager_decision, profile, memories,
        run_id, start_ms, total_input, total_output, model_calls, parse_retries, warnings, models_used, needs_memory
    ) -> CouncilResult:
        memory_context = "\n".join(record.content[:500] for record in memories)
        prompt = f"Task: {manager_decision.objective}"
        if memory_context:
            prompt += f"\nContext: {memory_context}"
        if manager_decision.constraints:
            prompt += f"\nConstraints: {', '.join(manager_decision.constraints)}"

        try:
            worker_result = await retry_completion(
                self.provider, "worker", prompt, _TOKEN_LIMITS[Budget.BALANCED],
                self.settings.retry_limit, profile=profile.value
            )
            model_calls += 1
            total_input += worker_result.input_tokens
            total_output += worker_result.output_tokens
            models_used["worker"] = worker_result.model
        except ProviderError as error:
            warnings.append(f"worker unavailable: {error.message}")
            end_ms = int(anyio.current_time() * 1000)
            return CouncilResult(
                status="error",
                run_id=run_id,
                route=Route.FULL,
                models=models_used,
                result=None,
                metrics=CouncilMetrics(
                    duration_ms=end_ms - start_ms,
                    input_tokens=total_input,
                    output_tokens=total_output,
                    model_calls=model_calls,
                    parse_retries=parse_retries,
                ),
                memory_updates=0,
                warnings=tuple(warnings),
            )

        critic_prompt = f"Original task: {manager_decision.objective}\n\nWorker response:\n{worker_result.content}"
        try:
            critic_result = await retry_completion(
                self.provider, "critic", critic_prompt, _TOKEN_LIMITS[Budget.LOW],
                self.settings.retry_limit, profile=None
            )
            model_calls += 1
            total_input += critic_result.input_tokens
            total_output += critic_result.output_tokens
            models_used["critic"] = critic_result.model
        except ProviderError as error:
            warnings.append(f"critic unavailable: {error.message}")
            end_ms = int(anyio.current_time() * 1000)
            return CouncilResult(
                status="partial",
                run_id=run_id,
                route=Route.FULL,
                models=models_used,
                result=worker_result.content,
                metrics=CouncilMetrics(
                    duration_ms=end_ms - start_ms,
                    input_tokens=total_input,
                    output_tokens=total_output,
                    model_calls=model_calls,
                    parse_retries=parse_retries,
                ),
                memory_updates=0,
                warnings=tuple(warnings),
            )

        verdict_data = _parse_json_response(critic_result.content)
        verdict = None
        if verdict_data:
            try:
                verdict = CriticVerdict(**verdict_data)
            except Exception:
                pass

        if verdict is None:
            fix_prompt = (
                "Your previous output was not valid JSON for CriticVerdict schema. "
                "Return ONLY the JSON object. No markdown, no code fences, no commentary.\n\n"
                f"Original task: {manager_decision.objective}\n"
                f"Worker response: {worker_result.content}"
            )
            try:
                retry = await retry_completion(
                    self.provider, "critic", fix_prompt, _TOKEN_LIMITS[Budget.LOW],
                    0, profile=None
                )
                parsed = _parse_json_response(retry.content)
                if parsed:
                    try:
                        verdict = CriticVerdict(**parsed)
                    except Exception:
                        pass
            except ProviderError:
                pass

        if verdict and verdict.verdict == Verdict.REJECT:
            max_rounds = self.settings.max_review_rounds
            for round_num in range(max_rounds):
                parse_retries += 1
                retry_prompt = f"Previous attempt was rejected.\nIssues: {[i.problem for i in verdict.issues]}\n\nPlease fix these issues and return corrected result."
                try:
                    worker_result = await retry_completion(
                        self.provider, "worker", retry_prompt, _TOKEN_LIMITS[Budget.BALANCED],
                        self.settings.retry_limit, profile=profile.value
                    )
                    model_calls += 1
                    total_input += worker_result.input_tokens
                    total_output += worker_result.output_tokens
                except ProviderError:
                    break

        synthesis_prompt = f"Task: {manager_decision.objective}\n\nWorker: {worker_result.content}\n\nCritic: {critic_result.content}"
        try:
            synthesis_result = await retry_completion(
                self.provider, "synthesizer", synthesis_prompt, _TOKEN_LIMITS[Budget.LOW],
                self.settings.retry_limit, profile=None
            )
            model_calls += 1
            total_input += synthesis_result.input_tokens
            total_output += synthesis_result.output_tokens
            models_used["synthesizer"] = synthesis_result.model
            final_result = synthesis_result.content
        except ProviderError:
            final_result = worker_result.content

        memory_updates = 0
        if needs_memory:
            memory_updates = await self._archive(request, str(run_id))

        status = "ok" if not warnings else "partial"
        await self.memory.commit_run(str(run_id), request.session_id, status, final_result)
        end_ms = int(anyio.current_time() * 1000)
        return CouncilResult(
            status=status,
            run_id=run_id,
            route=Route.FULL,
            models=models_used,
            result=final_result,
            metrics=CouncilMetrics(
                duration_ms=end_ms - start_ms,
                input_tokens=total_input,
                output_tokens=total_output,
                model_calls=model_calls,
                parse_retries=parse_retries,
            ),
            memory_updates=memory_updates,
            warnings=tuple(warnings),
        )

    async def _archive(self, request: CouncilRequest, run_id: str) -> int:
        if not self.settings.memory_extraction_enabled or contains_secret(request.task):
            return 0
        lowered = request.task.lower()
        if not any(
            marker in lowered for marker in ("prefer", "always", "project", "remember", "decision")
        ):
            return 0
        kind = MemoryKind.PREFERENCE if "prefer" in lowered else MemoryKind.PROJECT
        _, inserted = await self.memory.store(request.task, kind, source_run_id=run_id)
        return int(inserted)