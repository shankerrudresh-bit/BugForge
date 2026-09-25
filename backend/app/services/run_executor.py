"""Run executor — drives a chaos run step-by-step with observability."""
from __future__ import annotations

import asyncio
import datetime
import json
import logging

from sqlalchemy.orm import Session

from app.models.run import Run, RunStep, StepResult
from app.services import fault_engine
from app.services.observability import collect_logs, collect_metrics
from app.db import SessionLocal

logger = logging.getLogger(__name__)


async def execute_run(run_id: int) -> None:
    """Background coroutine: executes all steps of a chaos run."""
    db: Session = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is None:
            logger.error("Run %d not found", run_id)
            return

        run.status = "running"
        run.started_at = datetime.datetime.utcnow()
        db.commit()

        steps = db.query(RunStep).filter(RunStep.run_id == run_id).order_by(RunStep.step_index).all()

        overall_passed = True

        for step in steps:
            step.status = "running"
            step.started_at = datetime.datetime.utcnow()
            db.commit()

            params = json.loads(step.parameters_json) if step.parameters_json else {}

            # Start observability collectors for this step
            stop_event = asyncio.Event()
            collector_tasks = [
                asyncio.create_task(
                    collect_logs(step.target_service, run_id, step.id, stop_event, SessionLocal)
                ),
                asyncio.create_task(
                    collect_metrics(step.target_service, run_id, step.id, stop_event, SessionLocal)
                ),
            ]

            passed = True
            notes = ""

            try:
                # Apply fault
                await asyncio.to_thread(
                    fault_engine.apply_fault, step.fault_type, step.target_service, params
                )
                logger.info(
                    "Fault '%s' applied to '%s' for %ds",
                    step.fault_type,
                    step.target_service,
                    step.duration_seconds,
                )

                # Hold fault for duration
                await asyncio.sleep(step.duration_seconds)

            except Exception as exc:
                passed = False
                notes = f"Fault apply error: {exc}"
                logger.error("Step %d failed: %s", step.id, exc)
                overall_passed = False
            finally:
                # Stop collectors
                stop_event.set()
                await asyncio.gather(*collector_tasks, return_exceptions=True)

                # Revert fault (best-effort)
                try:
                    await asyncio.to_thread(
                        fault_engine.revert_fault, step.fault_type, step.target_service, params
                    )
                except Exception as exc:
                    logger.warning("Fault revert failed for step %d: %s", step.id, exc)

            # Determine pass/fail from logs
            if passed:
                error_logs = _count_error_logs(db, run_id, step.id)
                if error_logs > 0:
                    passed = False
                    notes = f"Detected {error_logs} error-level log line(s) during fault"
                    overall_passed = False

            step.status = "completed" if passed else "failed"
            step.finished_at = datetime.datetime.utcnow()

            result = StepResult(
                run_step_id=step.id,
                passed=passed,
                health_check_output=None,
                notes=notes,
            )
            db.add(result)
            db.commit()

        run.status = "completed" if overall_passed else "failed"
        run.finished_at = datetime.datetime.utcnow()
        db.commit()

        logger.info("Run %d finished with status '%s'", run_id, run.status)

    except Exception as exc:
        logger.exception("Unexpected error executing run %d: %s", run_id, exc)
        if db:
            run = db.get(Run, run_id)
            if run:
                run.status = "failed"
                run.finished_at = datetime.datetime.utcnow()
                db.commit()
    finally:
        db.close()


def _count_error_logs(db: Session, run_id: int, step_id: int) -> int:
    from app.models.observability import LogEntry

    entries = (
        db.query(LogEntry)
        .filter(LogEntry.run_id == run_id, LogEntry.run_step_id == step_id)
        .all()
    )
    keywords = ("error", "exception", "fatal", "critical", "traceback")
    return sum(
        1 for e in entries if any(k in e.message.lower() for k in keywords)
    )
