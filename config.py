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
        self.database_path: Path = self._get_database_path()

    def _get_environment(self) -> Environment:
        """Get the current environment."""
        env = os.getenv("JAMU_ENV", "prod").lower()
        if env in ("dev", "development"):
            return "dev"
        return "prod"

    def _get_database_path(self) -> Path:
        """Get the database path based on environment."""
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        db_name = "quotes_dev.db" if self.is_dev else "quotes.db"
        return data_dir / db_name

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
        return f"sqlite+aiosqlite:///{self.database_path}"

    @property
    def mode_display(self) -> str:
        """Get human-readable mode name."""
        return "DEVELOPMENT" if self.is_dev else "PRODUCTION"


# Global configuration instance
config = Config()