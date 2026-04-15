"""Database schema for Dalva experiment tracker."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import mapped_column, relationship

Base = declarative_base()


class Project(Base):
    """Project table for organizing experiments."""

    __tablename__ = "projects"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    name = mapped_column(String, unique=True, nullable=False, index=True)
    project_id = mapped_column(String, unique=True, nullable=False)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    runs = relationship("Run", back_populates="project", cascade="all, delete-orphan")
    custom_views = relationship(
        "CustomView", back_populates="project", cascade="all, delete-orphan"
    )
    dalva_tables = relationship(
        "DalvaTable", back_populates="project", cascade="all, delete-orphan"
    )


class Run(Base):
    """Run table for individual experiment runs."""

    __tablename__ = "runs"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    run_id = mapped_column(String, nullable=False)
    name = mapped_column(String)
    group_name = mapped_column(String, index=True)
    tags = mapped_column(Text)  # Comma-separated tags
    state = mapped_column(String, default="running", index=True)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_activity_at = mapped_column(
        DateTime, nullable=True
    )  # Tracks last log/finish request
    fork_from = mapped_column(Integer, nullable=True)  # Source run ID for forked runs

    # Relationships
    project = relationship("Project", back_populates="runs")
    metrics = relationship("Metric", back_populates="run", cascade="all, delete-orphan")
    configs = relationship("Config", back_populates="run", cascade="all, delete-orphan")
    files = relationship("File", back_populates="run", cascade="all, delete-orphan")
    dalva_tables = relationship(
        "DalvaTable", back_populates="run", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("project_id", "run_id", name="uq_project_run"),
        Index("idx_runs_project", "project_id"),
    )


class Metric(Base):
    """Metric table using EAV (Entity-Attribute-Value) model for flexibility."""

    __tablename__ = "metrics"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id = mapped_column(
        Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    attribute_path = mapped_column(String, nullable=False)
    attribute_type = mapped_column(String, nullable=False)
    step = mapped_column(Integer)
    timestamp = mapped_column(DateTime)
    float_value = mapped_column(Float)
    int_value = mapped_column(Integer)
    string_value = mapped_column(Text)
    bool_value = mapped_column(Boolean)

    # Relationship
    run = relationship("Run", back_populates="metrics")

    # Indexes for performance. The UNIQUE constraint on (run_id, attribute_path, step)
    # is created via raw SQL (COALESCE-based index) in connection.py because DuckDB
    # allows duplicate NULLs in standard UNIQUE constraints.
    __table_args__ = (
        Index("idx_metrics_run_attr", "run_id", "attribute_path"),
        Index("idx_metrics_run_step", "run_id", "step"),
        Index("idx_metrics_attr_type", "attribute_type"),
    )


class Config(Base):
    """Configuration/parameters table for experiment runs."""

    __tablename__ = "configs"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id = mapped_column(
        Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    key = mapped_column(String, nullable=False)
    value = mapped_column(Text)  # JSON-encoded value

    # Relationship
    run = relationship("Run", back_populates="configs")

    # Constraints
    __table_args__ = (
        UniqueConstraint("run_id", "key", name="uq_run_config_key"),
        Index("idx_configs_run", "run_id"),
    )


class File(Base):
    """Files metadata table for models, predictions, source code, etc."""

    __tablename__ = "files"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id = mapped_column(
        Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    file_type = mapped_column(
        String, nullable=False
    )  # model, prediction, source_code, sample_batch
    file_path = mapped_column(String, nullable=False)
    file_hash = mapped_column(String)
    size = mapped_column(Integer)
    file_metadata = mapped_column(
        Text
    )  # JSON (renamed from 'metadata' to avoid SQLAlchemy conflict)

    # Relationship
    run = relationship("Run", back_populates="files")

    # Indexes
    __table_args__ = (Index("idx_files_run_type", "run_id", "file_type"),)


class CustomView(Base):
    """Saved custom views with filters and column configurations."""

    __tablename__ = "custom_views"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name = mapped_column(String, nullable=False)
    filters = mapped_column(Text)  # JSON
    columns = mapped_column(Text)  # JSON
    sort_by = mapped_column(Text)  # JSON
    created_at = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    project = relationship("Project", back_populates="custom_views")


class DalvaTable(Base):
    """Table metadata for tabular data tracking."""

    __tablename__ = "dalva_tables"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    table_id = mapped_column(String, nullable=False)
    name = mapped_column(String)
    run_id = mapped_column(
        Integer, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True
    )
    version = mapped_column(Integer, default=0)
    row_count = mapped_column(Integer, default=0)
    column_schema = mapped_column(Text)  # JSON: [{"name": "col1", "type": "int"}, ...]
    config = mapped_column(Text)  # JSON
    state = mapped_column(String, default="active")  # active, finished
    created_at = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    project = relationship("Project", back_populates="dalva_tables")
    run = relationship("Run", back_populates="dalva_tables")
    rows = relationship(
        "DalvaTableRow", back_populates="table_record", cascade="all, delete-orphan"
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("project_id", "table_id", name="uq_project_table"),
        Index("idx_tables_project", "project_id"),
        Index("idx_tables_run", "run_id"),
        Index("idx_tables_table_id_version", "table_id", "version"),
    )


class DalvaTableRow(Base):
    """Individual rows stored as JSON for tabular data."""

    __tablename__ = "dalva_table_rows"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_id = mapped_column(
        Integer, ForeignKey("dalva_tables.id", ondelete="CASCADE"), nullable=False
    )
    version = mapped_column(Integer, default=0)
    row_data = mapped_column(Text)  # JSON: {"col1": val1, "col2": val2, ...}

    # Relationship
    table_record = relationship("DalvaTable", back_populates="rows")

    # Indexes
    __table_args__ = (Index("idx_table_rows_table_version", "table_id", "version"),)
