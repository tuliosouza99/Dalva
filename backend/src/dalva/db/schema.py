"""Database schema for Dalva experiment tracker."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Project(Base):
    """Project table for organizing experiments."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    project_id = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    runs = relationship("Run", back_populates="project", cascade="all, delete-orphan")
    custom_views = relationship(
        "CustomView", back_populates="project", cascade="all, delete-orphan"
    )
    dashboards = relationship(
        "Dashboard", back_populates="project", cascade="all, delete-orphan"
    )


class Run(Base):
    """Run table for individual experiment runs."""

    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    run_id = Column(String, nullable=False)
    name = Column(String)
    group_name = Column(String, index=True)
    tags = Column(Text)  # Comma-separated tags
    state = Column(String, default="running", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="runs")
    metrics = relationship("Metric", back_populates="run", cascade="all, delete-orphan")
    configs = relationship("Config", back_populates="run", cascade="all, delete-orphan")
    files = relationship("File", back_populates="run", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint("project_id", "run_id", name="uq_project_run"),
        Index("idx_runs_project", "project_id"),
    )


class Metric(Base):
    """Metric table using EAV (Entity-Attribute-Value) model for flexibility."""

    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    attribute_path = Column(String, nullable=False)
    attribute_type = Column(String, nullable=False)
    step = Column(Integer)
    timestamp = Column(DateTime)
    float_value = Column(Float)
    int_value = Column(Integer)
    string_value = Column(Text)
    bool_value = Column(Boolean)

    # Relationship
    run = relationship("Run", back_populates="metrics")

    # Indexes for performance
    __table_args__ = (
        Index("idx_metrics_run_attr", "run_id", "attribute_path"),
        Index("idx_metrics_run_step", "run_id", "step"),
        Index("idx_metrics_attr_type", "attribute_type"),
    )


class Config(Base):
    """Configuration/parameters table for experiment runs."""

    __tablename__ = "configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    key = Column(String, nullable=False)
    value = Column(Text)  # JSON-encoded value

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

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    file_type = Column(
        String, nullable=False
    )  # model, prediction, source_code, sample_batch
    file_path = Column(String, nullable=False)
    file_hash = Column(String)
    size = Column(Integer)
    file_metadata = Column(
        Text
    )  # JSON (renamed from 'metadata' to avoid SQLAlchemy conflict)

    # Relationship
    run = relationship("Run", back_populates="files")

    # Indexes
    __table_args__ = (Index("idx_files_run_type", "run_id", "file_type"),)


class CustomView(Base):
    """Saved custom views with filters and column configurations."""

    __tablename__ = "custom_views"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String, nullable=False)
    filters = Column(Text)  # JSON
    columns = Column(Text)  # JSON
    sort_by = Column(Text)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    project = relationship("Project", back_populates="custom_views")


class Dashboard(Base):
    """Dashboard configurations with widgets and layouts."""

    __tablename__ = "dashboards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String, nullable=False)
    widgets = Column(Text)  # JSON array of widget configs
    layout = Column(Text)  # JSON grid layout
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    project = relationship("Project", back_populates="dashboards")
