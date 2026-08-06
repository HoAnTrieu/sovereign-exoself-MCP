"""Validated boundary models."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Mode(StrEnum):
    AUTO = "auto"
    CODE = "code"
    ANALYSIS = "analysis"
    DECISION = "decision"


class Route(StrEnum):
    FAST = "fast"
    REVIEW = "review"
    FULL = "full"


class Budget(StrEnum):
    LOW = "low"
    BALANCED = "balanced"
    DEEP = "deep"


class OutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


class MemoryAction(StrEnum):
    SEARCH = "search"
    STORE = "store"
    LIST = "list"
    DELETE = "delete"
    EXPORT = "export"
    PROFILE = "profile"


class MemoryKind(StrEnum):
    PREFERENCE = "preference"
    FACT = "fact"
    PROJECT = "project"
    INSTRUCTION = "instruction"
    SUMMARY = "summary"


class TaskType(StrEnum):
    CODING = "coding"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"
    RESEARCH = "research"
    DOCUMENTATION = "documentation"
    PLANNING = "planning"
    DATA_ANALYSIS = "data_analysis"
    SYSTEM_OPERATION = "system_operation"
    GENERAL = "general"
    MEMORY = "memory"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ExpectedOutput(StrEnum):
    ANSWER = "answer"
    CODE = "code"
    PATCH = "patch"
    PATCH_AND_TESTS = "patch_and_tests"
    ANALYSIS = "analysis"
    PLAN = "plan"
    REPORT = "report"
    STRUCTURED_JSON = "structured_json"
    TOOL_RESULT = "tool_result"


class WorkerProfile(StrEnum):
    CODE_ENGINEER = "code_engineer"
    SYSTEM_ENGINEER = "system_engineer"
    RESEARCHER = "researcher"
    TECHNICAL_WRITER = "technical_writer"
    PLANNER = "planner"
    GENERAL_OPERATOR = "general_operator"


class Verdict(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class SynthesisStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    FAILED = "failed"


class MemoryStoreAction(StrEnum):
    NONE = "none"
    INSERT = "insert"
    UPDATE = "update"
    UPSERT = "upsert"
    DELETE = "delete"


class CouncilRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    task: str = Field(min_length=1, max_length=8000)
    mode: Mode = Mode.AUTO
    budget: Budget = Budget.LOW
    session_id: str | None = Field(default=None, max_length=128)
    output_format: OutputFormat = OutputFormat.TEXT
    worker_profile: WorkerProfile | None = None
    needs_memory: bool | None = None
    max_rounds: int | None = None
    route_override: Route | None = None


class ManagerDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_type: TaskType
    route: Route
    risk: RiskLevel
    worker_profile: WorkerProfile
    objective: str = Field(max_length=500)
    constraints: tuple[str, ...] = Field(default_factory=tuple, max_length=6)
    required_tools: tuple[str, ...] = Field(default_factory=tuple, max_length=5)
    expected_output: ExpectedOutput
    needs_memory: bool = False


class CriticIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    severity: str
    location: str
    problem: str
    fix: str


class CriticVerdict(BaseModel):
    model_config = ConfigDict(frozen=True)

    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    issues: tuple[CriticIssue, ...] = Field(default_factory=tuple, max_length=5)
    required_fixes: tuple[str, ...] = Field(default_factory=tuple)
    verification: tuple[str, ...] = Field(default_factory=tuple)


class SynthesisOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: SynthesisStatus
    summary: str
    result: dict | None = None
    files_changed: tuple[str, ...] = Field(default_factory=tuple)
    verification: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)
    next_action: str | None = None


class MemoryItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str
    key: str
    value: dict | str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class ArchivistOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    action: MemoryStoreAction
    memories: tuple[MemoryItem, ...] = Field(default_factory=tuple)


class ProviderResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str = Field(max_length=12000)
    model: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    cost: float | None = Field(default=None, ge=0)


class CouncilMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    duration_ms: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    model_calls: int = Field(ge=0)
    parse_retries: int = Field(ge=0)


class CouncilResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    run_id: UUID
    route: Route
    models: dict[str, str]
    result: dict | str | None = None
    metrics: CouncilMetrics
    memory_updates: int
    warnings: tuple[str, ...]


class MemoryRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    kind: MemoryKind
    content: str
    confidence: float
    importance: float
    active: bool