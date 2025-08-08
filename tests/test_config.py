"""Tests for configuration module."""

import os
from pathlib import Path

from config import Config


class TestConfig:
    def test_config_defaults(self, monkeypatch):
        monkeypatch.delenv("JAMU_ENV", raising=False)
        monkeypatch.delenv("DISCORD_TOKEN", raising=False)

        config = Config()

        assert config.env == "prod"
        assert config.is_prod is True
        assert config.is_dev is False
        assert config.command_prefix == "!"
        assert config.discord_token is None
        assert config.mode_display == "PRODUCTION"

    def test_config_dev_environment(self, monkeypatch):
        monkeypatch.setenv("JAMU_ENV", "dev")
        monkeypatch.setenv("DISCORD_TOKEN", "test_token_123")

        config = Config()

        assert config.env == "dev"
        assert config.is_dev is True
        assert config.is_prod is False
        assert config.command_prefix == "?"
        assert config.discord_token == "test_token_123"
        assert config.mode_display == "DEVELOPMENT"

    def test_config_development_environment(self, monkeypatch):
        monkeypatch.setenv("JAMU_ENV", "development")

        config = Config()

        assert config.env == "dev"
        assert config.is_dev is True
        assert config.command_prefix == "?"

    def test_config_prod_environment(self, monkeypatch):
        monkeypatch.setenv("JAMU_ENV", "prod")
        monkeypatch.setenv("DISCORD_TOKEN", "prod_token_456")

        config = Config()

        assert config.env == "prod"
        assert config.is_prod is True
        assert config.is_dev is False
        assert config.command_prefix == "!"
        assert config.discord_token == "prod_token_456"
        assert config.mode_display == "PRODUCTION"

    def test_config_invalid_environment(self, monkeypatch):
        monkeypatch.setenv("JAMU_ENV", "invalid")

        config = Config()

        assert config.env == "prod"
        assert config.is_prod is True
        assert config.command_prefix == "!"

    def test_database_path_dev(self, monkeypatch):
        monkeypatch.setenv("JAMU_ENV", "dev")

        config = Config()

        expected_path = Path("data") / "quotes_dev.db"
        assert config.database_path == expected_path
        assert "quotes_dev.db" in str(config.database_path)

    def test_database_path_prod(self, monkeypatch):
        monkeypatch.setenv("JAMU_ENV", "prod")

        config = Config()

        expected_path = Path("data") / "quotes.db"
        assert config.database_path == expected_path
        assert "quotes.db" in str(config.database_path)

    def test_database_url_format(self, monkeypatch):
        monkeypatch.setenv("JAMU_ENV", "dev")

        config = Config()

        expected_url = f"sqlite+aiosqlite:///{config.database_path}"
        assert config.database_url == expected_url
        assert config.database_url.startswith("sqlite+aiosqlite:///")
        assert "quotes_dev.db" in config.database_url

    def test_data_directory_creation(self, monkeypatch, tmp_path):
        monkeypatch.setenv("JAMU_ENV", "test")

        # Change to temporary directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Ensure data directory doesn't exist
            data_dir = Path("data")
            if data_dir.exists():
                data_dir.rmdir()

            Config()

            # Verify data directory was created
            assert data_dir.exists()
            assert data_dir.is_dir()
        finally:
            # Restore original directory
            os.chdir(original_cwd)

    def test_discord_token_none_when_not_set(self, monkeypatch):
        monkeypatch.delenv("DISCORD_TOKEN", raising=False)

        config = Config()

        assert config.discord_token is None

    def test_discord_token_empty_string(self, monkeypatch):
        monkeypatch.setenv("DISCORD_TOKEN", "")

        config = Config()

        assert config.discord_token == ""

    def test_config_case_insensitive_env(self, monkeypatch):
        test_cases = ["DEV", "Dev", "DEVELOPMENT", "Development", "PROD", "Prod"]

        for env_value in test_cases:
            monkeypatch.setenv("JAMU_ENV", env_value)
            config = Config()

            if env_value.lower() in ("dev", "development"):
                assert config.env == "dev"
                assert config.command_prefix == "?"
            else:
                assert config.env == "prod"
                assert config.command_prefix == "!"

    def test_config_properties_are_consistent(self, monkeypatch):
        # Test dev environment
        monkeypatch.setenv("JAMU_ENV", "dev")
        config = Config()

        assert config.is_dev == (config.env == "dev")
        assert config.is_prod == (config.env == "prod")
        assert config.is_dev != config.is_prod

        # Test prod environment
        monkeypatch.setenv("JAMU_ENV", "prod")
        config = Config()

        assert config.is_dev == (config.env == "dev")
        assert config.is_prod == (config.env == "prod")
        assert config.is_dev != config.is_prod

    def test_config_mode_display_values(self, monkeypatch):
        # Test development
        monkeypatch.setenv("JAMU_ENV", "dev")
        config = Config()
        assert config.mode_display == "DEVELOPMENT"

        # Test production
        monkeypatch.setenv("JAMU_ENV", "prod")
        config = Config()
        assert config.mode_display == "PRODUCTION"
