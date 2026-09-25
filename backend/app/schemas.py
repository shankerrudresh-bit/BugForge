from __future__ import annotations
import datetime
from typing import Any, List, Optional
from pydantic import BaseModel


# ── Service description inside an Architecture ──────────────────────────────

class ServiceDefinition(BaseModel):
    name: str
    type: str                          # e.g. "database", "api", "cache", "worker"
    dependencies: List[str] = []
    slo_latency_ms: Optional[int] = None
    slo_availability_pct: Optional[float] = None


# ── Architecture ─────────────────────────────────────────────────────────────

class ArchitectureCreate(BaseModel):
    name: str
    description: Optional[str] = None
    services: List[ServiceDefinition]


class ArchitectureResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    services_json: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# ── Fault step inside a Scenario ────────────────────────────────────────────

class FaultStep(BaseModel):
    step_index: int
    fault_type: str          # kill_container | pause_container | network_partition | cpu_stress | memory_stress | inject_latency
    target_service: str
    duration_seconds: int = 30
    parameters: dict[str, Any] = {}
    description: Optional[str] = None


# ── Scenario ─────────────────────────────────────────────────────────────────

class ScenarioGenerateRequest(BaseModel):
    architecture_id: int
    num_scenarios: int = 3


class ScenarioStatusUpdate(BaseModel):
    status: str   # approved | rejected


class ScenarioResponse(BaseModel):
    id: int
    architecture_id: int
    title: str
    description: Optional[str]
    steps_json: str
    status: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# ── Run ───────────────────────────────────────────────────────────────────────

class RunCreate(BaseModel):
    scenario_id: int


class StepResultResponse(BaseModel):
    id: int
    run_step_id: int
    passed: bool
    health_check_output: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


class RunStepResponse(BaseModel):
    id: int
    run_id: int
    step_index: int
    fault_type: str
    target_service: str
    parameters_json: Optional[str]
    duration_seconds: int
    status: str
    started_at: Optional[datetime.datetime]
    finished_at: Optional[datetime.datetime]
    result: Optional[StepResultResponse] = None

    class Config:
        from_attributes = True


class RunResponse(BaseModel):
    id: int
    scenario_id: int
    status: str
    started_at: Optional[datetime.datetime]
    finished_at: Optional[datetime.datetime]
    steps: List[RunStepResponse] = []

    class Config:
        from_attributes = True


# ── Observability ─────────────────────────────────────────────────────────────

class LogEntryResponse(BaseModel):
    id: int
    run_id: int
    run_step_id: Optional[int]
    container_name: str
    timestamp: datetime.datetime
    message: str

    class Config:
        from_attributes = True


class MetricSampleResponse(BaseModel):
    id: int
    run_id: int
    run_step_id: Optional[int]
    container_name: str
    cpu_pct: float
    mem_mb: float
    sampled_at: datetime.datetime

    class Config:
        from_attributes = True


# ── Report ────────────────────────────────────────────────────────────────────

class StepSummary(BaseModel):
    step_index: int
    fault_type: str
    target_service: str
    duration_seconds: int
    status: str
    passed: bool
    peak_cpu_pct: float
    peak_mem_mb: float
    error_log_count: int
    health_check_output: Optional[str]


class RunReportResponse(BaseModel):
    run_id: int
    scenario_id: int
    scenario_title: str
    overall_passed: bool
    steps: List[StepSummary]
    narrative: Optional[str] = None
