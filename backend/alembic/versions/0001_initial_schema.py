"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "architectures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("services_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_architectures_id", "architectures", ["id"])

    op.create_table(
        "scenarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("architecture_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("steps_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["architecture_id"], ["architectures.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenarios_id", "scenarios", ["id"])
    op.create_index("ix_scenarios_architecture_id", "scenarios", ["architecture_id"])

    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runs_id", "runs", ["id"])
    op.create_index("ix_runs_scenario_id", "runs", ["scenario_id"])

    op.create_table(
        "run_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("fault_type", sa.String(50), nullable=False),
        sa.Column("target_service", sa.String(255), nullable=False),
        sa.Column("parameters_json", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_run_steps_id", "run_steps", ["id"])
    op.create_index("ix_run_steps_run_id", "run_steps", ["run_id"])

    op.create_table(
        "step_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_step_id", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("health_check_output", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_step_id"], ["run_steps.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_step_id"),
    )

    op.create_table(
        "log_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("run_step_id", sa.Integer(), nullable=True),
        sa.Column("container_name", sa.String(255), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["run_step_id"], ["run_steps.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_log_entries_run_id", "log_entries", ["run_id"])
    op.create_index("ix_log_entries_run_step_id", "log_entries", ["run_step_id"])

    op.create_table(
        "metric_samples",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("run_step_id", sa.Integer(), nullable=True),
        sa.Column("container_name", sa.String(255), nullable=False),
        sa.Column("cpu_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("mem_mb", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "sampled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["run_step_id"], ["run_steps.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metric_samples_run_id", "metric_samples", ["run_id"])
    op.create_index("ix_metric_samples_run_step_id", "metric_samples", ["run_step_id"])


def downgrade() -> None:
    op.drop_table("metric_samples")
    op.drop_table("log_entries")
    op.drop_table("step_results")
    op.drop_table("run_steps")
    op.drop_table("runs")
    op.drop_table("scenarios")
    op.drop_table("architectures")
