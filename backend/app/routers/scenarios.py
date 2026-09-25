"""Scenarios router."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.architecture import Architecture
from app.models.scenario import Scenario
from app.schemas import (
    ArchitectureCreate,
    ScenarioGenerateRequest,
    ScenarioResponse,
    ScenarioStatusUpdate,
    ServiceDefinition,
)
from app.services import llm_service

router = APIRouter(tags=["scenarios"])


@router.post("/scenarios/generate", response_model=list[ScenarioResponse], status_code=201)
def generate_scenarios(payload: ScenarioGenerateRequest, db: Session = Depends(get_db)):
    arch = db.get(Architecture, payload.architecture_id)
    if arch is None:
        raise HTTPException(status_code=404, detail="Architecture not found")

    # Reconstruct ArchitectureCreate for the LLM service
    services = [ServiceDefinition(**s) for s in json.loads(arch.services_json)]
    arch_schema = ArchitectureCreate(
        name=arch.name,
        description=arch.description,
        services=services,
    )

    try:
        raw_scenarios = llm_service.generate_scenarios(arch_schema, payload.num_scenarios)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {exc}")

    created = []
    for raw in raw_scenarios:
        scenario = Scenario(
            architecture_id=arch.id,
            title=raw.get("title", "Untitled Scenario"),
            description=raw.get("description"),
            steps_json=json.dumps(raw.get("steps", [])),
            status="draft",
        )
        db.add(scenario)
        db.flush()
        created.append(scenario)

    db.commit()
    for s in created:
        db.refresh(s)
    return created


@router.get("/architectures/{arch_id}/scenarios", response_model=list[ScenarioResponse])
def list_scenarios(arch_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Scenario)
        .filter(Scenario.architecture_id == arch_id)
        .order_by(Scenario.id.desc())
        .all()
    )


@router.get("/scenarios/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    scenario = db.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.patch("/scenarios/{scenario_id}/status", response_model=ScenarioResponse)
def update_scenario_status(
    scenario_id: int, payload: ScenarioStatusUpdate, db: Session = Depends(get_db)
):
    scenario = db.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if payload.status not in ("approved", "rejected", "draft"):
        raise HTTPException(status_code=400, detail="Status must be approved, rejected, or draft")
    scenario.status = payload.status
    db.commit()
    db.refresh(scenario)
    return scenario
