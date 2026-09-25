"""Architectures router."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.architecture import Architecture
from app.schemas import ArchitectureCreate, ArchitectureResponse

router = APIRouter(tags=["architectures"])


@router.post("/architectures", response_model=ArchitectureResponse, status_code=201)
def create_architecture(payload: ArchitectureCreate, db: Session = Depends(get_db)):
    arch = Architecture(
        name=payload.name,
        description=payload.description,
        services_json=json.dumps([s.model_dump() for s in payload.services]),
    )
    db.add(arch)
    db.commit()
    db.refresh(arch)
    return arch


@router.get("/architectures", response_model=list[ArchitectureResponse])
def list_architectures(db: Session = Depends(get_db)):
    return db.query(Architecture).order_by(Architecture.id.desc()).all()


@router.get("/architectures/{arch_id}", response_model=ArchitectureResponse)
def get_architecture(arch_id: int, db: Session = Depends(get_db)):
    arch = db.get(Architecture, arch_id)
    if arch is None:
        raise HTTPException(status_code=404, detail="Architecture not found")
    return arch
