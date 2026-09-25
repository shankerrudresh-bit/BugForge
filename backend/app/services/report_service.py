"""Report service — builds a structured pass/fail report for a completed run."""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.run import Run, RunStep, StepResult
from app.models.observability import LogEntry, MetricSample
from app.models.scenario import Scenario
from app.schemas import RunReportResponse, StepSummary
from app.services import llm_service
from app.config import settings

logger = logging.getLogger(__name__)


def build_report(run_id: int, db: Session) -> RunReportResponse:
    run = db.get(Run, run_id)
    if run is None:
        raise ValueError(f"Run {run_id} not found")

    scenario = db.get(Scenario, run.scenario_id)
    steps = (
        db.query(RunStep)
        .filter(RunStep.run_id == run_id)
        .order_by(RunStep.step_index)
        .all()
    )

    step_summaries: list[StepSummary] = []

    for step in steps:
        result: Optional[StepResult] = (
            db.query(StepResult).filter(StepResult.run_step_id == step.id).first()
        )
        metrics = (
            db.query(MetricSample)
            .filter(
                MetricSample.run_id == run_id,
                MetricSample.run_step_id == step.id,
            )
            .all()
        )
        logs = (
            db.query(LogEntry)
            .filter(
                LogEntry.run_id == run_id,
                LogEntry.run_step_id == step.id,
            )
            .all()
        )

        peak_cpu = max((m.cpu_pct for m in metrics), default=0.0)
        peak_mem = max((m.mem_mb for m in metrics), default=0.0)
        keywords = ("error", "exception", "fatal", "critical", "traceback")
        error_log_count = sum(
            1 for e in logs if any(k in e.message.lower() for k in keywords)
        )

        passed = result.passed if result else (step.status == "completed")

        step_summaries.append(
            StepSummary(
                step_index=step.step_index,
                fault_type=step.fault_type,
                target_service=step.target_service,
                duration_seconds=step.duration_seconds,
                status=step.status,
                passed=passed,
                peak_cpu_pct=round(peak_cpu, 2),
                peak_mem_mb=round(peak_mem, 2),
                error_log_count=error_log_count,
                health_check_output=result.health_check_output if result else None,
            )
        )

    overall_passed = all(s.passed for s in step_summaries)

    narrative: Optional[str] = None
    if settings.LLM_REPORT_NARRATIVE:
        run_summary = {
            "run_id": run_id,
            "scenario": scenario.title if scenario else "unknown",
            "steps": [s.model_dump() for s in step_summaries],
        }
        narrative = llm_service.generate_narrative(run_summary)

    return RunReportResponse(
        run_id=run_id,
        scenario_id=run.scenario_id,
        scenario_title=scenario.title if scenario else "Unknown",
        overall_passed=overall_passed,
        steps=step_summaries,
        narrative=narrative,
    )
