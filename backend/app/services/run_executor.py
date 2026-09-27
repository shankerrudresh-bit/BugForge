"""Run executor — drives a chaos run step-by-step (synchronous, runs in a thread)."""
from __future__ import annotations

import datetime
import json
import logging
import time

from sqlalchemy.orm import Session

from app.models.run import Run, RunStep, StepResult
from app.models.observability import LogEntry, MetricSample
from app.services import fault_engine
from app.db import SessionLocal

logger = logging.getLogger(__name__)


def execute_run(run_id: int) -> None:
    """Synchronous run executor — called in a daemon thread from the runs router."""
    db: Session = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is None:
            logger.error("Run %d not found", run_id)
            return

        run.status = "running"
        run.started_at = datetime.datetime.utcnow()
        db.commit()
        logger.info("Run %d started", run_id)

        steps = (
            db.query(RunStep)
            .filter(RunStep.run_id == run_id)
            .order_by(RunStep.step_index)
            .all()
        )

        overall_passed = True

        for step in steps:
            step.status = "running"
            step.started_at = datetime.datetime.utcnow()
            db.commit()
            logger.info("Step %d starting: %s -> %s", step.id, step.fault_type, step.target_service)

            params = json.loads(step.parameters_json) if step.parameters_json else {}
            passed = True
            notes = ""

            # ── Apply fault ───────────────────────────────────────────────────
            try:
                fault_engine.apply_fault(step.fault_type, step.target_service, params)
                logger.info("Fault applied: %s on %s", step.fault_type, step.target_service)
            except Exception as exc:
                passed = False
                notes = f"Fault apply error: {exc}"
                logger.error("Step %d fault apply failed: %s", step.id, exc)
                overall_passed = False

            # ── Hold duration then collect some logs/metrics inline ───────────
            duration = step.duration_seconds if passed else 0
            _collect_during_step(db, run_id, step.id, step.target_service, duration)

            # ── Revert fault (best-effort) ────────────────────────────────────
            try:
                fault_engine.revert_fault(step.fault_type, step.target_service, params)
                logger.info("Fault reverted: %s on %s", step.fault_type, step.target_service)
            except Exception as exc:
                logger.warning("Fault revert failed for step %d: %s", step.id, exc)

            # ── Evaluate pass/fail from captured logs ─────────────────────────
            if passed:
                error_count = _count_error_logs(db, run_id, step.id)
                if error_count > 0:
                    passed = False
                    notes = f"Detected {error_count} error-level log line(s) during fault"
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
            logger.info("Step %d finished: passed=%s", step.id, passed)

        run.status = "completed" if overall_passed else "failed"
        run.finished_at = datetime.datetime.utcnow()
        db.commit()
        logger.info("Run %d completed with status '%s'", run_id, run.status)

    except Exception as exc:
        logger.exception("Unexpected error in run %d: %s", run_id, exc)
        try:
            run = db.get(Run, run_id)
            if run:
                run.status = "failed"
                run.finished_at = datetime.datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _collect_during_step(
    db: Session, run_id: int, step_id: int, service_name: str, duration: int
) -> None:
    """Collect metrics + logs every 2 seconds for `duration` seconds (blocking)."""
    try:
        import docker as docker_sdk
        from app.config import settings
        client = docker_sdk.DockerClient(base_url=f"unix://{settings.DOCKER_SOCKET_PATH}")

        # find container
        containers = client.containers.list()
        container = next((c for c in containers if service_name in c.name), None)

        if container is None:
            logger.warning("Collector: container '%s' not found", service_name)
            time.sleep(duration)
            return

        elapsed = 0
        interval = 2
        while elapsed < duration:
            sleep_time = min(interval, duration - elapsed)
            time.sleep(sleep_time)
            elapsed += sleep_time

            # Capture a metric sample
            try:
                stats = container.stats(stream=False)
                cpu_pct = _cpu_pct(stats)
                mem_mb = _mem_mb(stats)
                sample = MetricSample(
                    run_id=run_id,
                    run_step_id=step_id,
                    container_name=container.name,
                    cpu_pct=cpu_pct,
                    mem_mb=mem_mb,
                    sampled_at=datetime.datetime.utcnow(),
                )
                db.add(sample)
            except Exception as exc:
                logger.debug("Metric sample failed: %s", exc)

            # Capture recent log lines
            try:
                since = datetime.datetime.utcnow() - datetime.timedelta(seconds=interval + 1)
                raw_logs = container.logs(since=since, timestamps=True)
                for line in raw_logs.decode("utf-8", errors="replace").splitlines():
                    if line.strip():
                        entry = LogEntry(
                            run_id=run_id,
                            run_step_id=step_id,
                            container_name=container.name,
                            message=line.strip(),
                            timestamp=datetime.datetime.utcnow(),
                        )
                        db.add(entry)
            except Exception as exc:
                logger.debug("Log capture failed: %s", exc)

            db.commit()

    except Exception as exc:
        logger.warning("Collector setup failed: %s — sleeping %ds", exc, duration)
        time.sleep(duration)


def _cpu_pct(stats: dict) -> float:
    try:
        cpu_delta = (
            stats["cpu_stats"]["cpu_usage"]["total_usage"]
            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        )
        sys_delta = (
            stats["cpu_stats"]["system_cpu_usage"]
            - stats["precpu_stats"]["system_cpu_usage"]
        )
        cpus = stats["cpu_stats"].get("online_cpus") or len(
            stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [1])
        )
        return round((cpu_delta / sys_delta) * cpus * 100.0, 2) if sys_delta else 0.0
    except Exception:
        return 0.0


def _mem_mb(stats: dict) -> float:
    try:
        usage = stats["memory_stats"]["usage"]
        cache = stats["memory_stats"].get("stats", {}).get("cache", 0)
        return round((usage - cache) / (1024 * 1024), 2)
    except Exception:
        return 0.0


def _count_error_logs(db: Session, run_id: int, step_id: int) -> int:
    entries = (
        db.query(LogEntry)
        .filter(LogEntry.run_id == run_id, LogEntry.run_step_id == step_id)
        .all()
    )
    keywords = ("error", "exception", "fatal", "critical", "traceback")
    return sum(1 for e in entries if any(k in e.message.lower() for k in keywords))
