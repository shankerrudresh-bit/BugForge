import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Boolean, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scenario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scenarios.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | running | completed | failed
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    steps = relationship("RunStep", back_populates="run", order_by="RunStep.step_index")


class RunStep(Base):
    __tablename__ = "run_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runs.id"), nullable=False, index=True
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    fault_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_service: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters_json: Mapped[str] = mapped_column(Text, nullable=True)  # JSON object
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | running | completed | failed
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run = relationship("Run", back_populates="steps")
    result = relationship("StepResult", back_populates="step", uselist=False)


class StepResult(Base):
    __tablename__ = "step_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_step_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("run_steps.id"), nullable=False, unique=True
    )
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    health_check_output: Mapped[str] = mapped_column(Text, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    step = relationship("RunStep", back_populates="result")
