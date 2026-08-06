"""MCP stdio server exposing exactly three public tools."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import assert_never

from mcp.server.mcpserver import MCPServer

from sovereign_exoself_mcp import __version__
from sovereign_exoself_mcp.council import Council
from sovereign_exoself_mcp.domain import (
    Budget,
    CouncilRequest,
    MemoryAction,
    MemoryKind,
    Mode,
    OutputFormat,
    Route,
    WorkerProfile,
)
from sovereign_exoself_mcp.memory import SCHEMA_VERSION, MemoryRepository
from sovereign_exoself_mcp.prompts import get_all_versions
from sovereign_exoself_mcp.providers import (
    DeterministicMockProvider,
    LiteLLMOllamaProvider,
    LiteLLMOpenRouterProvider,
    OllamaModels,
    Provider,
    probe_ollama,
)
from sovereign_exoself_mcp.settings import Settings, load_env_file


class Application:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.memory = MemoryRepository(settings.database_path)
        self.active_runs = 0
        match settings.provider_mode:
            case "openrouter":
                # Load local secrets (e.g. OPENROUTER_API_KEY) from the
                # gitignored project `.env` only when the real OpenRouter
                # provider is actually selected. Mock/ollama paths never touch
                # `.env`, keeping the test suite hermetic.
                load_env_file()
                key = os.environ.get("OPENROUTER_API_KEY", "")
                self.provider: Provider = LiteLLMOpenRouterProvider(key, "openrouter/auto")
            case "ollama":
                self.provider = LiteLLMOllamaProvider(
                    models=OllamaModels(
                        manager=settings.ollama_manager_model,
                        worker=settings.ollama_worker_model,
                        critic=settings.ollama_critic_model,
                        synthesizer=settings.ollama_synthesizer_model,
                        archivist=settings.ollama_archivist_model,
                    ),
                    api_base=settings.ollama_api_base,
                    timeout_seconds=settings.provider_timeout_seconds,
                )
            case "mock":
                self.provider = DeterministicMockProvider(
                    delay_seconds=settings.mock_delay_seconds,
                    failure_roles=frozenset(filter(None, settings.mock_failure_roles.split(","))),
                )
            case unexpected:
                assert_never(unexpected)
        self.council = Council(settings, self.memory, self.provider)

    async def start(self) -> None:
        await self.memory.open()

    async def stop(self) -> None:
        await self.memory.close()


def create_server(settings: Settings | None = None) -> MCPServer:
    runtime = Application(settings or Settings())

    @asynccontextmanager
    async def lifespan(_: MCPServer) -> AsyncIterator[Application]:
        await runtime.start()
        try:
            yield runtime
        finally:
            await runtime.stop()

    server = MCPServer(name="sovereign-exoself", version=__version__, lifespan=lifespan)

    @server.tool(name="council_run", description="Run the bounded personal council.")
    async def council_run(
        task: str,
        mode: str = "auto",
        budget: str = "low",
        session_id: str | None = None,
        output_format: str = "text",
        worker_profile: str | None = None,
        needs_memory: bool | None = None,
        max_rounds: int | None = None,
        route_override: str | None = None,
    ) -> dict[str, object]:
        runtime.active_runs += 1
        try:
            profile = WorkerProfile(worker_profile) if worker_profile else None
            # `mode` accepts either a genuine council mode (auto/code/analysis/
            # decision) or a shorthand route name (fast/review/full). An
            # explicit `route_override` argument always wins.
            resolved_route = None
            if mode in ("fast", "review", "full"):
                resolved_route = Route(mode)
                effective_mode = Mode.AUTO
            else:
                effective_mode = Mode(mode)
            if route_override is not None:
                resolved_route = Route(route_override)
            request = CouncilRequest(
                task=task,
                mode=effective_mode,
                budget=Budget(budget),
                session_id=session_id,
                output_format=OutputFormat(output_format),
                worker_profile=profile,
                needs_memory=needs_memory,
                max_rounds=max_rounds,
                route_override=resolved_route,
            )
            result = await runtime.council.run(request)
            return {
                "run_id": str(result.run_id),
                "status": result.status,
                "route": result.route.value,
                "models": result.models,
                "result": result.result,
                "metrics": result.metrics.model_dump(mode="json"),
                "memory_updates": result.memory_updates,
                "warnings": result.warnings,
            }
        finally:
            runtime.active_runs -= 1

    @server.tool(
        name="memory_manage", description="Search, store, list, delete, export, or profile memory."
    )
    async def memory_manage(
        action: str,
        query: str | None = None,
        content: str | None = None,
        memory_id: str | None = None,
        limit: int = 10,
        kind: str | None = None,
    ) -> dict[str, object]:
        parsed = MemoryAction(action)
        if parsed is MemoryAction.SEARCH:
            records = await runtime.memory.search(query or "", limit)
            return {"items": [record.model_dump(mode="json") for record in records]}
        if parsed is MemoryAction.STORE:
            if content is None or kind is None:
                return {"error": "content and kind are required"}
            item_id, inserted = await runtime.memory.store(content, MemoryKind(kind))
            return {"id": item_id, "inserted": inserted}
        if parsed is MemoryAction.LIST:
            records = await runtime.memory.list(limit)
            return {"items": [record.model_dump(mode="json") for record in records]}
        if parsed is MemoryAction.DELETE:
            return {"deleted": await runtime.memory.delete(memory_id or "")}
        if parsed is MemoryAction.EXPORT:
            return {"json": await runtime.memory.export()}
        records = await runtime.memory.list(limit)
        return {"count": len(records), "kinds": sorted({record.kind.value for record in records})}

    @server.tool(
        name="system_status", description="Return local health without calling a provider."
    )
    async def system_status() -> dict[str, object]:
        ollama = await probe_ollama(
            runtime.settings.ollama_api_base, runtime.settings.provider_timeout_seconds
        )
        return {
            "version": __version__,
            "mcp_sdk_version": "2.0.0",
            "database_path": str(runtime.settings.database_path),
            "database_schema_version": SCHEMA_VERSION,
            "provider_mode": runtime.settings.provider_mode,
            "max_concurrent_workers": runtime.settings.max_concurrent_workers,
            "thinking_enabled": runtime.settings.think,
            "prompt_versions": get_all_versions(),
            "model_mapping": {
                "manager": runtime.settings.ollama_manager_model,
                "worker": runtime.settings.ollama_worker_model,
                "critic": runtime.settings.ollama_critic_model,
                "synthesizer": runtime.settings.ollama_synthesizer_model,
                "archivist": runtime.settings.ollama_archivist_model,
            },
            "active_runs": runtime.active_runs,
            "last_successful_run": await runtime.memory.last_successful_run(),
            "health": "ok",
            "live_openrouter_available": bool(os.environ.get("OPENROUTER_API_KEY")),
            "ollama_available": ollama.available,
            "ollama_api_base": runtime.settings.ollama_api_base,
            "ollama_models": list(ollama.models),
        }

    return server