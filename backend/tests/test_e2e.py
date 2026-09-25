"""
End-to-end integration test.

Covers the full happy path:
  create architecture → generate scenarios (mocked LLM) → approve → create run →
  poll until complete → fetch report

Run with:
  pytest backend/tests/test_e2e.py -v
  (requires DATABASE_URL env pointing to a live test Postgres)
"""
from __future__ import annotations

import json
import time
import os
import pytest
import httpx

BASE_URL = os.environ.get("TEST_API_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


def test_health(client: httpx.Client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_architecture(client: httpx.Client):
    payload = {
        "name": "E2E Test Architecture",
        "description": "Automated test architecture",
        "services": [
            {
                "name": "api",
                "type": "api",
                "dependencies": ["db"],
                "slo_latency_ms": 200,
                "slo_availability_pct": 99.9,
            },
            {
                "name": "db",
                "type": "database",
                "dependencies": [],
                "slo_latency_ms": 50,
                "slo_availability_pct": 99.99,
            },
        ],
    }
    r = client.post("/api/architectures", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["name"] == "E2E Test Architecture"
    assert data["id"] > 0
    return data["id"]


def test_get_architecture(client: httpx.Client):
    # Create one first
    r = client.post(
        "/api/architectures",
        json={
            "name": "Fetch Test",
            "services": [{"name": "svc", "type": "api", "dependencies": []}],
        },
    )
    arch_id = r.json()["id"]
    r2 = client.get(f"/api/architectures/{arch_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == arch_id


def test_full_flow(client: httpx.Client):
    """Full E2E: architecture → scenarios → approve → run → report."""
    # 1. Create architecture
    arch_r = client.post(
        "/api/architectures",
        json={
            "name": "E2E Full Flow",
            "description": "Full flow test",
            "services": [
                {"name": "web", "type": "api", "dependencies": ["cache", "postgres"]},
                {"name": "cache", "type": "cache", "dependencies": []},
                {"name": "postgres", "type": "database", "dependencies": []},
            ],
        },
    )
    assert arch_r.status_code == 201, arch_r.text
    arch_id = arch_r.json()["id"]

    # 2. Generate scenarios (requires real LLM configured in env)
    gen_r = client.post(
        "/api/scenarios/generate",
        json={"architecture_id": arch_id, "num_scenarios": 1},
    )
    # If LLM isn't configured skip execution test
    if gen_r.status_code == 502:
        pytest.skip("LLM not configured — skipping scenario generation test")
    assert gen_r.status_code == 201, gen_r.text
    scenarios = gen_r.json()
    assert len(scenarios) >= 1
    scenario_id = scenarios[0]["id"]

    # 3. Approve first scenario
    approve_r = client.patch(
        f"/api/scenarios/{scenario_id}/status",
        json={"status": "approved"},
    )
    assert approve_r.status_code == 200
    assert approve_r.json()["status"] == "approved"

    # 4. Create run
    run_r = client.post("/api/runs", json={"scenario_id": scenario_id})
    assert run_r.status_code == 201, run_r.text
    run_id = run_r.json()["id"]

    # 5. Poll until terminal (max 5 minutes for fault durations)
    deadline = time.time() + 300
    status = "pending"
    while time.time() < deadline:
        poll_r = client.get(f"/api/runs/{run_id}")
        assert poll_r.status_code == 200
        status = poll_r.json()["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(5)

    assert status in ("completed", "failed"), f"Run timed out in status: {status}"

    # 6. Fetch report
    report_r = client.get(f"/api/runs/{run_id}/report")
    assert report_r.status_code == 200, report_r.text
    report = report_r.json()
    assert report["run_id"] == run_id
    assert "steps" in report
    assert isinstance(report["overall_passed"], bool)


def test_scenario_status_validation(client: httpx.Client):
    arch_r = client.post(
        "/api/architectures",
        json={
            "name": "Status Validation Test",
            "services": [{"name": "svc", "type": "api", "dependencies": []}],
        },
    )
    arch_id = arch_r.json()["id"]

    # Insert a manual draft scenario via architecture list endpoint
    gen_r = client.post(
        "/api/scenarios/generate",
        json={"architecture_id": arch_id, "num_scenarios": 1},
    )
    if gen_r.status_code == 502:
        pytest.skip("LLM not configured")
    scenario_id = gen_r.json()[0]["id"]

    # Attempt to run a draft scenario — should fail with 400
    run_r = client.post("/api/runs", json={"scenario_id": scenario_id})
    assert run_r.status_code == 400
    assert "approved" in run_r.json()["detail"].lower()
