"""Fault injection engine — applies and reverts Docker-level faults."""
from __future__ import annotations

import logging
from enum import Enum

try:
    import docker
    from docker.errors import DockerException
    _DOCKER_AVAILABLE = True
except ImportError:
    _DOCKER_AVAILABLE = False
    DockerException = Exception  # type: ignore[misc,assignment]

from app.config import settings

logger = logging.getLogger(__name__)


class FaultType(str, Enum):
    kill_container = "kill_container"
    pause_container = "pause_container"
    network_partition = "network_partition"
    cpu_stress = "cpu_stress"
    memory_stress = "memory_stress"
    inject_latency = "inject_latency"


def _get_client():
    if not _DOCKER_AVAILABLE:
        raise RuntimeError(
            "Docker SDK is not installed. Run: pip install docker\n"
            "Also ensure Docker Desktop is running."
        )
    return docker.DockerClient(base_url=f"unix://{settings.DOCKER_SOCKET_PATH}")


def _get_container(client: docker.DockerClient, service_name: str):
    """Resolve a Docker Compose service name to a running container.

    Docker Compose names containers as <project>-<service>-<index>.
    We do a partial name match to stay project-agnostic.
    """
    containers = client.containers.list()
    for c in containers:
        if service_name in c.name:
            return c
    raise LookupError(
        f"No running container found matching service name '{service_name}'. "
        f"Running containers: {[c.name for c in containers]}"
    )


def apply_fault(fault_type: str, target_service: str, parameters: dict) -> None:
    """Apply the specified fault to the target service container."""
    client = _get_client()
    container = _get_container(client, target_service)
    params = parameters or {}

    logger.info("Applying fault '%s' to container '%s'", fault_type, container.name)

    if fault_type == FaultType.kill_container:
        container.kill()

    elif fault_type == FaultType.pause_container:
        container.pause()

    elif fault_type == FaultType.network_partition:
        networks = list(container.attrs["NetworkSettings"]["Networks"].keys())
        for net_name in networks:
            network = client.networks.get(net_name)
            network.disconnect(container)
        logger.info("Disconnected container from networks: %s", networks)

    elif fault_type == FaultType.cpu_stress:
        cores = params.get("cpu_cores", 1)
        load = params.get("load_pct", 80)
        cmd = f"stress-ng --cpu {cores} --cpu-load {load} --timeout {params.get('duration_seconds', 30)}s &"
        container.exec_run(cmd, detach=True)

    elif fault_type == FaultType.memory_stress:
        mem_mb = params.get("memory_mb", 256)
        cmd = f"stress-ng --vm 1 --vm-bytes {mem_mb}M --timeout {params.get('duration_seconds', 30)}s &"
        container.exec_run(cmd, detach=True)

    elif fault_type == FaultType.inject_latency:
        delay_ms = params.get("delay_ms", 200)
        jitter_ms = params.get("jitter_ms", 50)
        cmd = f"tc qdisc add dev eth0 root netem delay {delay_ms}ms {jitter_ms}ms"
        exit_code, output = container.exec_run(cmd)
        if exit_code != 0:
            logger.warning("tc netem apply failed (code %d): %s", exit_code, output)

    else:
        raise ValueError(f"Unknown fault type: {fault_type}")


def revert_fault(fault_type: str, target_service: str, parameters: dict) -> None:
    """Revert the specified fault from the target service container."""
    try:
        client = _get_client()
        container = _get_container(client, target_service)
    except (DockerException, LookupError) as exc:
        logger.warning("Could not find container to revert fault: %s", exc)
        return

    logger.info("Reverting fault '%s' on container '%s'", fault_type, container.name)

    if fault_type == FaultType.kill_container:
        container.start()

    elif fault_type == FaultType.pause_container:
        container.unpause()

    elif fault_type == FaultType.network_partition:
        # Reconnect to the default bridge network; best-effort
        try:
            networks = client.networks.list(names=["bridge"])
            if networks:
                networks[0].connect(container)
        except Exception as exc:
            logger.warning("Could not reconnect container to network: %s", exc)

    elif fault_type in (FaultType.cpu_stress, FaultType.memory_stress):
        # stress-ng exits on its own after timeout; kill any remaining instances
        container.exec_run("pkill -f stress-ng", detach=True)

    elif fault_type == FaultType.inject_latency:
        cmd = "tc qdisc del dev eth0 root"
        exit_code, output = container.exec_run(cmd)
        if exit_code != 0:
            logger.warning("tc netem revert failed (code %d): %s", exit_code, output)

    else:
        logger.warning("No revert logic for fault type: %s", fault_type)
