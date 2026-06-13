"""Configuration module for Jamu Bot."""

import os
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

Environment = Literal["dev", "prod"]

# libpq-style query parameters that asyncpg does not accept on the URL. They
# are stripped from the URL and translated into connect_args where needed.
_LIBPQ_ONLY_PARAMS = ("sslmode", "channel_binding")
# sslmode values that mean "encryption is required".
_SSL_REQUIRED_MODES = ("require", "verify-ca", "verify-full")


class Config:
    """Application configuration."""

    def __init__(self) -> None:
        self.env: Environment = self._get_environment()
        self.discord_token: str | None = os.getenv("DISCORD_TOKEN")
        self.command_prefix: str = "?" if self.is_dev else "!"
        # Full connection string (e.g. from Neon or any managed provider). When
        # set it takes precedence over the individual POSTGRES_* settings below.
        self.database_url_override: str | None = os.getenv("DATABASE_URL")
        self.postgres_host: str = os.getenv("POSTGRES_HOST", "postgres")
        self.postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
        self.postgres_db: str = os.getenv("POSTGRES_DB", "jamu_quotes")
        self.postgres_user: str = os.getenv("POSTGRES_USER", "jamu_bot")
        self.postgres_password: str | None = os.getenv("POSTGRES_PASSWORD")
        # Explicit SSL override: "require" forces TLS, "disable" turns it off.
        # When unset, SSL is inferred from the connection string.
        self.db_ssl: str | None = os.getenv("DB_SSL")
        # asyncpg caches prepared statements per connection, which breaks behind
        # transaction-mode poolers such as Neon's PgBouncer endpoint. 0 disables
        # the cache and is the safe default for serverless/pooled databases.
        self.db_statement_cache_size: int = int(
            os.getenv("DB_STATEMENT_CACHE_SIZE", "0")
        )
        # Recycle pooled connections so idle ones dropped by the provider (Neon
        # auto-suspends) are not handed out stale.
        self.db_pool_recycle: int = int(os.getenv("DB_POOL_RECYCLE", "300"))

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

    def _resolve_url_and_ssl(self) -> tuple[str, bool]:
        """Resolve the SQLAlchemy URL and whether TLS is required.

        Returns the driver-qualified URL with libpq-only query parameters
        stripped, plus a flag indicating that the connection requires SSL.
        """
        if self.database_url_override:
            return self._normalize_url(self.database_url_override)

        if not self.postgres_password:
            raise ValueError("POSTGRES_PASSWORD environment variable is required")
        url = (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
        return url, False

    @staticmethod
    def _normalize_url(raw: str) -> tuple[str, bool]:
        """Normalize a raw connection string for the asyncpg driver.

        Rewrites the scheme to ``postgresql+asyncpg`` and removes libpq-only
        query parameters (``sslmode``, ``channel_binding``) that asyncpg cannot
        parse, returning whether ``sslmode`` requested encryption.
        """
        parts = urlsplit(raw)
        scheme = parts.scheme
        if scheme in ("postgres", "postgresql"):
            scheme = "postgresql+asyncpg"

        query_pairs = parse_qsl(parts.query, keep_blank_values=True)
        sslmode = None
        kept_pairs = []
        for key, value in query_pairs:
            if key == "sslmode":
                sslmode = value
            if key in _LIBPQ_ONLY_PARAMS:
                continue
            kept_pairs.append((key, value))

        ssl_required = sslmode in _SSL_REQUIRED_MODES
        new_query = urlencode(kept_pairs)
        url = urlunsplit((scheme, parts.netloc, parts.path, new_query, parts.fragment))
        return url, ssl_required

    @property
    def database_url(self) -> str:
        """Get the database URL for SQLAlchemy (asyncpg driver)."""
        return self._resolve_url_and_ssl()[0]

    @property
    def connect_args(self) -> dict[str, Any]:
        """Driver-level connect arguments for the async engine."""
        url, ssl_required = self._resolve_url_and_ssl()
        if not url.startswith("postgresql"):
            return {}

        args: dict[str, Any] = {"statement_cache_size": self.db_statement_cache_size}
        if self.db_ssl == "require" or (ssl_required and self.db_ssl != "disable"):
            args["ssl"] = True
        return args

    @property
    def engine_options(self) -> dict[str, Any]:
        """Keyword arguments for ``create_async_engine``.

        Adds pooling resilience and driver connect args for PostgreSQL so the
        same configuration works against local Docker and managed providers
        like Neon without code changes.
        """
        url = self.database_url
        options: dict[str, Any] = {"echo": False}
        if url.startswith("postgresql"):
            options["pool_pre_ping"] = True
            options["pool_recycle"] = self.db_pool_recycle
            options["connect_args"] = self.connect_args
        return options

    @property
    def mode_display(self) -> str:
        """Get human-readable mode name."""
        return "DEVELOPMENT" if self.is_dev else "PRODUCTION"


# Global configuration instance
config = Config()
