"""Configuration module for Jamu Bot."""

import os
from pathlib import Path
from typing import Literal

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

Environment = Literal["dev", "prod"]


class Config:
    """Application configuration."""

    def __init__(self) -> None:
        self.env: Environment = self._get_environment()
        self.discord_token: str | None = os.getenv("DISCORD_TOKEN")
        self.command_prefix: str = "?" if self.is_dev else "!"
        self.postgres_host: str = os.getenv("POSTGRES_HOST", "postgres")
        self.postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
        self.postgres_db: str = os.getenv("POSTGRES_DB", "jamu_quotes")
        self.postgres_user: str = os.getenv("POSTGRES_USER", "jamu_bot")
        self.postgres_password: str | None = os.getenv("POSTGRES_PASSWORD")

    def _get_environment(self) -> Environment:
        """Get the current environment."""
        env = os.getenv("JAMU_ENV", "prod").lower()
        if env in ("dev", "development"):
            return "dev"
        return "prod"


    @property
    def is_dev(self) -> bool:
        """Check if running in development mode."""
        return self.env == "dev"

    @property
    def is_prod(self) -> bool:
        """Check if running in production mode."""
        return self.env == "prod"

    @property
    def database_url(self) -> str:
        """Get the database URL for SQLAlchemy."""
        if not self.postgres_password:
            raise ValueError("POSTGRES_PASSWORD environment variable is required")
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def mode_display(self) -> str:
        """Get human-readable mode name."""
        return "DEVELOPMENT" if self.is_dev else "PRODUCTION"


# Global configuration instance
config = Config()
