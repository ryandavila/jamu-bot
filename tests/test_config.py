"""Tests for configuration module."""

import os
from pathlib import Path

from bot.config import Config


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

    def test_postgres_config(self, monkeypatch):
        monkeypatch.setenv("POSTGRES_HOST", "localhost")
        monkeypatch.setenv("POSTGRES_PORT", "5432")
        monkeypatch.setenv("POSTGRES_DB", "test_db")
        monkeypatch.setenv("POSTGRES_USER", "test_user")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test_pass")

        config = Config()

        assert config.postgres_host == "localhost"
        assert config.postgres_port == 5432
        assert config.postgres_db == "test_db"
        assert config.postgres_user == "test_user"
        assert config.postgres_password == "test_pass"

    def test_database_url_format(self, monkeypatch):
        monkeypatch.setenv("POSTGRES_HOST", "localhost")
        monkeypatch.setenv("POSTGRES_PORT", "5432")
        monkeypatch.setenv("POSTGRES_DB", "jamu_quotes")
        monkeypatch.setenv("POSTGRES_USER", "jamu_bot")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test_password")

        config = Config()

        expected_url = "postgresql+asyncpg://jamu_bot:test_password@localhost:5432/jamu_quotes"
        assert config.database_url == expected_url
        assert config.database_url.startswith("postgresql+asyncpg://")
        assert "jamu_quotes" in config.database_url

    def test_database_url_requires_password(self, monkeypatch):
        monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

        config = Config()

        # Should raise ValueError when accessing database_url without password
        try:
            _ = config.database_url
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "POSTGRES_PASSWORD" in str(e)

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
