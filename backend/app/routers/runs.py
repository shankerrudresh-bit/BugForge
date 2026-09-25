"""Runs router — create and monitor chaos runs."""
import asyncio
import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.run import Run, RunStep
from app.models.scenario import Scenario
from app.models.observability import LogEntry, MetricSample
from app.schemas import (
    RunCreate,
    RunResponse,
    RunStepResponse,
    LogEntryResponse,
    MetricSampleResponse,
    RunReportResponse,
)
from app.services.run_executor import execute_run
from app.services.report_service import build_report

router = APIRouter(tags=["runs"])


def _enqueue_run(run_id: int) -> None:
    """Entry point for BackgroundTasks — bridges sync→async."""
    asyncio.run(execute_run(run_id))


@router.post("/runs", response_model=RunResponse, status_code=201)
def create_run(
    payload: RunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    scenario = db.get(Scenario, payload.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if scenario.status != "approved":
        raise HTTPException(
            status_code=400,
            detail="Only approved scenarios can be executed. Approve the scenario first.",
        )

    steps_raw = json.loads(scenario.steps_json)

    run = Run(scenario_id=scenario.id, status="pending")
    db.add(run)
    db.flush()

    for raw_step in steps_raw:
        step = RunStep(
            run_id=run.id,
            step_index=raw_step.get("step_index", 0),
            fault_type=raw_step.get("fault_type", "kill_container"),
            target_service=raw_step.get("target_service", ""),
            parameters_json=json.dumps(raw_step.get("parameters", {})),
            duration_seconds=int(raw_step.get("duration_seconds", 30)),
            status="pending",
        )
        db.add(step)

    db.commit()
    db.refresh(run)

    background_tasks.add_task(_enqueue_run, run.id)

    return run


@router.get("/runs", response_model=list[RunResponse])
def list_runs(scenario_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Run)
    if scenario_id is not None:
        q = q.filter(Run.scenario_id == scenario_id)
    return q.order_by(Run.id.desc()).all()


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/runs/{run_id}/steps", response_model=list[RunStepResponse])
def get_run_steps(run_id: int, db: Session = Depends(get_db)):
    return (
        db.query(RunStep)
        .filter(RunStep.run_id == run_id)
        .order_by(RunStep.step_index)
        .all()
    )


@router.get("/runs/{run_id}/logs", response_model=list[LogEntryResponse])
def get_run_logs(
    run_id: int,
    step_id: Optional[int] = Query(None),
    container: Optional[str] = Query(None),
    limit: int = Query(200),
    db: Session = Depends(get_db),
):
    q = db.query(LogEntry).filter(LogEntry.run_id == run_id)
    if step_id is not None:
        q = q.filter(LogEntry.run_step_id == step_id)
    if container:
        q = q.filter(LogEntry.container_name == container)
    return q.order_by(LogEntry.timestamp.asc()).limit(limit).all()


@router.get("/runs/{run_id}/metrics", response_model=list[MetricSampleResponse])
def get_run_metrics(
    run_id: int,
    step_id: Optional[int] = Query(None),
    container: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(MetricSample).filter(MetricSample.run_id == run_id)
    if step_id is not None:
        q = q.filter(MetricSample.run_step_id == step_id)
    if container:
        q = q.filter(MetricSample.container_name == container)
    return q.order_by(MetricSample.sampled_at.asc()).all()


@router.get("/runs/{run_id}/report", response_model=RunReportResponse)
def get_run_report(run_id: int, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status not in ("completed", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Run is still '{run.status}'. Report is available after the run completes.",
        )
    return build_report(run_id, db)
