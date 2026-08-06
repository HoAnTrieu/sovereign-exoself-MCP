"""Provider boundary with mock and LiteLLM implementations."""

import json
import random
import time
from dataclasses import dataclass, field
from typing import Protocol
from urllib.request import Request, urlopen

import anyio

from sovereign_exoself_mcp.domain import ProviderResult
from sovereign_exoself_mcp.prompts import build_system_prompt


class ProviderError(Exception):
    """Provider failure with retry metadata."""

    def __init__(self, message: str, *, transient: bool, retry_after: float | None = None) -> None:
        self.message = message
        self.transient = transient
        self.retry_after = retry_after
        super().__init__(message)


class Provider(Protocol):
    """Minimal normalized model-provider contract."""

    async def complete(self, role: str, prompt: str, budget: int, profile: str | None = None) -> ProviderResult: ...


@dataclass(frozen=True, slots=True)
class OllamaModels:
    manager: str
    worker: str
    critic: str
    synthesizer: str
    archivist: str

    def for_role(self, role: str) -> str:
        models = {
            "manager": self.manager,
            "worker": self.worker,
            "engineer": self.worker,
            "analyst": self.worker,
            "critic": self.critic,
            "synthesizer": self.synthesizer,
            "archivist": self.archivist,
        }
        try:
            return models[role]
        except KeyError as error:
            raise ProviderError(f"unknown Ollama role {role}", transient=False) from error


@dataclass(frozen=True, slots=True)
class OllamaStatus:
    available: bool
    models: tuple[str, ...]


@dataclass(slots=True)
class DeterministicMockProvider:
    """Predictable local provider used for all non-live verification."""

    delay_seconds: float = 0
    failure_roles: frozenset[str] = field(default_factory=frozenset)
    calls: list[str] = field(default_factory=list)

    async def complete(self, role: str, prompt: str, budget: int, profile: str | None = None) -> ProviderResult:
        self.calls.append(role)
        if self.delay_seconds:
            await anyio.sleep(self.delay_seconds)
        if role in self.failure_roles:
            raise ProviderError(f"mock failure for {role}", transient=False)
        content = self._content(role, prompt)
        return ProviderResult(
            content=content[: budget * 8],
            model="deterministic-mock",
            input_tokens=min(len(prompt.split()), 100),
            output_tokens=min(len(content.split()), budget),
            latency_ms=int(self.delay_seconds * 1000),
            cost=0,
        )

    @staticmethod
    def _content(role: str, prompt: str) -> str:
        match role:
            case "manager":
                return json.dumps({
                    "task_type": "coding",
                    "route": "fast",
                    "risk": "low",
                    "worker_profile": "code_engineer",
                    "objective": prompt[:100],
                    "expected_output": "answer",
                    "needs_memory": False,
                    "constraints": [],
                    "required_tools": [],
                })
            case "engineer":
                return json.dumps({"content": f"Engineering view: {prompt[-500:]}"})
            case "analyst":
                return json.dumps({"content": f"Analysis view: {prompt[-500:]}"})
            case "worker":
                return json.dumps({"content": f"Worker view: {prompt[-500:]}"})
            case "critic":
                return json.dumps({
                    "verdict": "APPROVE",
                    "confidence": 0.95,
                    "issues": [],
                    "required_fixes": [],
                    "verification": ["Mock verification passed"],
                })
            case "synthesizer":
                return json.dumps({
                    "status": "completed",
                    "summary": f"Synthesis: {prompt[-200:]}",
                    "result": {},
                    "files_changed": [],
                    "verification": [],
                    "warnings": [],
                    "next_action": None,
                })
            case "archivist":
                return json.dumps({"action": "skip", "reason": "Mock skip"})
            case unexpected:
                raise ProviderError(f"unknown role {unexpected}", transient=False)


@dataclass(frozen=True, slots=True)
class LiteLLMOpenRouterProvider:
    """OpenRouter adapter isolated from LiteLLM response shapes."""

    api_key: str
    model: str

    async def complete(self, role: str, prompt: str, budget: int, profile: str | None = None) -> ProviderResult:
        started = time.perf_counter()
        try:
            import litellm

            system_prompt = build_system_prompt(role, profile)
            response = await litellm.acompletion(
                model=self.model
                if self.model.startswith("openrouter/")
                else f"openrouter/{self.model}",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=budget,
                api_key=self.api_key,
            )
        except (TimeoutError, OSError) as error:
            raise ProviderError(str(error), transient=True) from error
        content = str(response.choices[0].message.content or "")
        usage = response.usage
        return ProviderResult(
            content=content,
            model=str(response.model),
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            latency_ms=int((time.perf_counter() - started) * 1000),
            cost=None,
        )


@dataclass(frozen=True, slots=True)
class LiteLLMOllamaProvider:
    models: OllamaModels
    api_base: str
    timeout_seconds: float

    async def complete(self, role: str, prompt: str, budget: int, profile: str | None = None) -> ProviderResult:
        import litellm
        from litellm.exceptions import (
            APIConnectionError,
            APIError,
            BadRequestError,
            InternalServerError,
            ServiceUnavailableError,
        )
        from litellm.exceptions import (
            Timeout as LiteLLMTimeout,
        )

        model = self.models.for_role(role)
        system_prompt = build_system_prompt(role, profile)
        started = time.perf_counter()
        try:
            with anyio.fail_after(self.timeout_seconds):
                response = await litellm.acompletion(
                    model=f"ollama/{model}",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=budget,
                    api_base=self.api_base,
                    timeout=self.timeout_seconds,
                )
        except (TimeoutError, LiteLLMTimeout) as error:
            raise ProviderError(
                f"Ollama request timed out after {self.timeout_seconds:g} seconds",
                transient=True,
            ) from error
        except (OSError, APIConnectionError) as error:
            raise ProviderError(
                f"Ollama unavailable at {self.api_base}: {error}", transient=True
            ) from error
        except BadRequestError as error:
            raise ProviderError(
                f"Ollama rejected model {model}: {error}", transient=False
            ) from error
        except (
            APIError,
            InternalServerError,
            ServiceUnavailableError,
        ) as error:
            raise ProviderError(
                f"Ollama request failed at {self.api_base}: {error}", transient=True
            ) from error
        content = str(response.choices[0].message.content or "")
        usage = response.usage
        return ProviderResult(
            content=content,
            model=str(response.model),
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            latency_ms=int((time.perf_counter() - started) * 1000),
            cost=None,
        )


def _read_ollama_status(api_base: str, timeout_seconds: float) -> OllamaStatus:
    request = Request(f"{api_base.rstrip('/')}/api/tags", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=min(timeout_seconds, 1.0)) as response:
            payload = json.load(response)
    except OSError, json.JSONDecodeError, UnicodeError:
        return OllamaStatus(available=False, models=())

    models = payload.get("models", []) if isinstance(payload, dict) else []
    names: list[str] = []
    if isinstance(models, list):
        for model in models:
            if isinstance(model, dict):
                name = model.get("name")
                if isinstance(name, str):
                    names.append(name)
    return OllamaStatus(available=True, models=tuple(sorted(names)))


async def probe_ollama(api_base: str, timeout_seconds: float) -> OllamaStatus:
    return await anyio.to_thread.run_sync(_read_ollama_status, api_base, timeout_seconds)


def is_retryable(error: ProviderError) -> bool:
    """Classify normalized provider errors."""
    return error.transient


async def retry_completion(
    provider: Provider, role: str, prompt: str, budget: int, retries: int, profile: str | None = None
) -> ProviderResult:
    """Use bounded exponential retry only for normalized transient failures."""
    for attempt in range(retries + 1):
        try:
            return await provider.complete(role, prompt, budget, profile)
        except ProviderError as error:
            if not is_retryable(error) or attempt == retries:
                raise
            delay = (
                error.retry_after
                if error.retry_after is not None
                else (2**attempt) + random.random()
            )
            await anyio.sleep(delay)
    raise ProviderError("retry loop exhausted", transient=False)
