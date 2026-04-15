"""Tests for configuration management."""

from pathlib import Path

from dalva.config import (
    DalvaConfig,
    DatabaseConfig,
    get_database_config,
    load_config,
    save_config,
)


class TestDatabaseConfig:
    """Tests for DatabaseConfig model."""

    def test_default_values(self):
        """Test that DatabaseConfig has correct defaults."""

        config = DatabaseConfig()
        assert config.db_path == str(Path.home() / ".dalva" / "dalva.duckdb")

    def test_custom_values(self):
        """Test that DatabaseConfig accepts custom values."""

        config = DatabaseConfig(
            db_path="/custom/path/db.duckdb",
        )
        assert config.db_path == "/custom/path/db.duckdb"


class TestDalvaConfig:
    """Tests for DalvaConfig model."""

    def test_default_database_config(self):
        """Test that DalvaConfig has default database config."""

        config = DalvaConfig()
        assert isinstance(config.database, DatabaseConfig)
        assert "database" in DalvaConfig.model_fields


class TestConfigFileOperations:
    """Tests for config file save and load operations."""

    def test_save_and_load_config(self, temp_config_dir, monkeypatch):
        """Test saving and loading configuration."""
        # Clear DALVA_DB_PATH to avoid interference from other tests
        monkeypatch.delenv("DALVA_DB_PATH", raising=False)

        # Ensure config dir exists
        temp_config_dir.mkdir(parents=True, exist_ok=True)

        # Patch CONFIG_FILE to use temp location
        monkeypatch.setattr("dalva.config.CONFIG_FILE", temp_config_dir / "config.json")

        # Create and save config
        config = DalvaConfig(
            database=DatabaseConfig(
                db_path="/test/db.duckdb",
            )
        )
        save_config(config)

        # Verify file was created
        config_file = temp_config_dir / "config.json"
        assert config_file.exists()

        # Load and verify
        loaded = load_config()
        assert loaded.database.db_path == "/test/db.duckdb"

    def test_load_config_nonexistent_file(self, temp_config_dir, monkeypatch):
        """Test that load_config works when no config file exists."""
        # Patch CONFIG_FILE to use non-existent location
        monkeypatch.setattr(
            "dalva.config.CONFIG_FILE", temp_config_dir / "nonexistent.json"
        )

        # Should return default config without error
        config = load_config()
        assert config.database.db_path is not None

    def test_load_config_invalid_json(self, temp_config_dir, monkeypatch):
        """Test that load_config handles invalid JSON gracefully."""
        # Create invalid JSON file
        temp_config_dir.mkdir(parents=True, exist_ok=True)
        invalid_file = temp_config_dir / "config.json"
        invalid_file.write_text("{ invalid json }")

        # Patch CONFIG_FILE
        monkeypatch.setattr("dalva.config.CONFIG_FILE", invalid_file)

        # Should return default config with warning
        config = load_config()
        assert config.database.db_path is not None


class TestEnvironmentVariables:
    """Tests for environment variable overrides."""

    def test_env_var_override_db_path(self, monkeypatch):
        """Test that DALVA_DB_PATH environment variable overrides config."""

        # Set environment variable
        monkeypatch.setenv("DALVA_DB_PATH", "/env/db.duckdb")

        config = load_config()
        assert config.database.db_path == "/env/db.duckdb"


class TestGetDatabaseConfig:
    """Tests for get_database_config helper function."""

    def test_get_database_config_returns_db_config(self):
        """Test that get_database_config returns DatabaseConfig."""

        config = get_database_config()
        assert config.db_path is not None
