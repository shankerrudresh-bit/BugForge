import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class LogEntry(Base):
    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runs.id"), nullable=False, index=True
    )
    run_step_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("run_steps.id"), nullable=True, index=True
    )
    container_name: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)


class MetricSample(Base):
    __tablename__ = "metric_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runs.id"), nullable=False, index=True
    )
    run_step_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("run_steps.id"), nullable=True, index=True
    )
    container_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cpu_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mem_mb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sampled_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
