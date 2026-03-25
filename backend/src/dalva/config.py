"""Configuration management for Dalva."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database configuration.

    The database always lives at ``db_path`` on the local filesystem.
    """

    db_path: str = str(Path.home() / ".dalva" / "dalva.duckdb")


class DalvaConfig(BaseModel):
    """Dalva configuration."""

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)


# Configuration file location
CONFIG_DIR = Path.home() / ".dalva"
CONFIG_FILE = CONFIG_DIR / "config.json"
ENV_FILE = CONFIG_DIR / ".env"


def load_config() -> DalvaConfig:
    """
    Load configuration from file and environment variables.

    Priority: Environment variables > Config file > Defaults

    Returns:
        DalvaConfig: The loaded configuration
    """
    # Load .env file if it exists
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)

    config = DalvaConfig()

    # Load from config file if exists
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
                config = DalvaConfig(**data)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to load config file: {e}")
            print("Using default configuration")

    # Override with environment variables
    if os.getenv("DALVA_DB_PATH"):
        config.database.db_path = os.getenv("DALVA_DB_PATH")  # type: ignore

    return config


def save_config(config: DalvaConfig) -> None:
    """
    Save configuration to file.

    Args:
        config: Configuration to save
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config.model_dump(), f, indent=2)


def get_database_config() -> DatabaseConfig:
    """
    Get database configuration.

    Returns:
        DatabaseConfig: Database configuration
    """
    return load_config().database
