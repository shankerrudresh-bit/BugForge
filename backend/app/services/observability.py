"""Observability collector — streams logs and metrics from Docker containers."""
from __future__ import annotations

import asyncio
import datetime
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

try:
    import docker
    _DOCKER_AVAILABLE = True
except ImportError:
    _DOCKER_AVAILABLE = False

from sqlalchemy.orm import Session

from app.config import settings
from app.models.observability import LogEntry, MetricSample

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=16)


def _get_client():
    if not _DOCKER_AVAILABLE:
        raise RuntimeError("Docker SDK not available. pip install docker")
    return docker.DockerClient(base_url=f"unix://{settings.DOCKER_SOCKET_PATH}")


def _find_container(client: docker.DockerClient, service_name: str):
    containers = client.containers.list()
    for c in containers:
        if service_name in c.name:
            return c
    return None


# ── Log collection ────────────────────────────────────────────────────────────

def _stream_logs_blocking(
    service_name: str,
    run_id: int,
    step_id: int | None,
    stop_event: threading.Event,
    db_factory,
) -> None:
    """Blocking function executed in a thread pool."""

    client = _get_client()
    container = _find_container(client, service_name)
    if container is None:
        logger.warning("Log collector: container '%s' not found", service_name)
        return

    db: Session = db_factory()
    try:
        for raw_line in container.logs(stream=True, follow=True, timestamps=True):
            if stop_event.is_set():
                break
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            entry = LogEntry(
                run_id=run_id,
                run_step_id=step_id,
                container_name=container.name,
                message=line,
                timestamp=datetime.datetime.utcnow(),
            )
            db.add(entry)
            db.commit()
    except Exception as exc:
        logger.warning("Log streaming error for '%s': %s", service_name, exc)
    finally:
        db.close()


async def collect_logs(
    service_name: str,
    run_id: int,
    step_id: int | None,
    stop_event: asyncio.Event,
    db_factory,
) -> None:
    """Async wrapper: runs blocking log stream in a thread."""
    thread_stop = threading.Event()

    async def _watch_asyncio_event():
        await stop_event.wait()
        thread_stop.set()

    asyncio.create_task(_watch_asyncio_event())
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        _executor,
        _stream_logs_blocking,
        service_name,
        run_id,
        step_id,
        thread_stop,
        db_factory,
    )


# ── Metric collection ─────────────────────────────────────────────────────────

def _stream_metrics_blocking(
    service_name: str,
    run_id: int,
    step_id: int | None,
    stop_event,
    db_factory,
) -> None:
    client = _get_client()
    container = _find_container(client, service_name)
    if container is None:
        logger.warning("Metric collector: container '%s' not found", service_name)
        return

    db: Session = db_factory()
    try:
        for raw_stats in container.stats(stream=True, decode=True):
            if stop_event.is_set():
                break
            try:
                cpu_pct = _compute_cpu_pct(raw_stats)
                mem_mb = _compute_mem_mb(raw_stats)
            except (KeyError, ZeroDivisionError):
                continue

            sample = MetricSample(
                run_id=run_id,
                run_step_id=step_id,
                container_name=container.name,
                cpu_pct=cpu_pct,
                mem_mb=mem_mb,
                sampled_at=datetime.datetime.utcnow(),
            )
            db.add(sample)
            db.commit()
    except Exception as exc:
        logger.warning("Metric streaming error for '%s': %s", service_name, exc)
    finally:
        db.close()


async def collect_metrics(
    service_name: str,
    run_id: int,
    step_id: int | None,
    stop_event: asyncio.Event,
    db_factory,
) -> None:
    thread_stop = threading.Event()

    async def _watch():
        await stop_event.wait()
        thread_stop.set()

    asyncio.create_task(_watch())
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        _executor,
        _stream_metrics_blocking,
        service_name,
        run_id,
        step_id,
        thread_stop,
        db_factory,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_cpu_pct(stats: dict) -> float:
    cpu_delta = (
        stats["cpu_stats"]["cpu_usage"]["total_usage"]
        - stats["precpu_stats"]["cpu_usage"]["total_usage"]
    )
    system_delta = (
        stats["cpu_stats"]["system_cpu_usage"]
        - stats["precpu_stats"]["system_cpu_usage"]
    )
    num_cpus = stats["cpu_stats"].get("online_cpus") or len(
        stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [1])
    )
    if system_delta == 0:
        return 0.0
    return (cpu_delta / system_delta) * num_cpus * 100.0


def _compute_mem_mb(stats: dict) -> float:
    mem_usage = stats["memory_stats"]["usage"]
    cache = stats["memory_stats"].get("stats", {}).get("cache", 0)
    return (mem_usage - cache) / (1024 * 1024)
