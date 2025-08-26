"""Pytest configuration and fixtures for Jamu Bot tests."""

import asyncio
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import Config
from models import Base


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path() -> Generator[Path]:
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    yield db_path

    # Clean up
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def test_config(temp_db_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    """Create a test configuration with temporary database."""
    # Set environment to test
    monkeypatch.setenv("JAMU_ENV", "dev")
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)

    # Create config and override database path
    config = Config()
    config.database_path = temp_db_path

    return config


@pytest_asyncio.fixture
async def test_db_engine(test_config: Config):
    """Create a test database engine."""
    engine = create_async_engine(test_config.database_url, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession]:
    """Create a test database session."""
    async_session = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
def mock_bot():
    """Create a mock Discord bot for testing."""
    intents = None  # We don't need real intents for testing
    bot = commands.Bot(command_prefix="!", intents=intents)
    return bot


@pytest.fixture
def mock_guild():
    """Create a mock Discord guild."""

    class MockGuild:
        def __init__(self):
            self.id = 123456789
            self.name = "Test Guild"
            self.channels = []

        def get_channel(self, channel_id: int):
            return next((c for c in self.channels if c.id == channel_id), None)

    return MockGuild()


@pytest.fixture
def mock_channel():
    """Create a mock Discord channel."""

    class MockChannel:
        def __init__(self):
            self.id = 987654321
            self.name = "test-channel"
            self.guild = None

        async def fetch_message(self, message_id: int):
            # Mock message for testing
            class MockMessage:
                def __init__(self):
                    self.id = message_id
                    self.content = "Test message content"

                    # Create a simple mock user inline to avoid circular reference
                    class MockMessageAuthor:
                        def __init__(self):
                            self.id = 999999999
                            self.name = "MessageAuthor"
                            self.display_name = "MessageAuthor"

                    self.author = MockMessageAuthor()
                    self.created_at = None
                    self.channel = MockChannel()

            return MockMessage()

    return MockChannel()


@pytest.fixture
def mock_user():
    """Create a mock Discord user."""

    class MockUser:
        def __init__(self):
            self.id = 111111111
            self.name = "TestUser"
            self.display_name = "TestUser"
            self.guild_permissions = MockPermissions()

    class MockPermissions:
        def __init__(self):
            self.administrator = False
            self.view_channel = True

    return MockUser()


@pytest.fixture
def mock_member(mock_user, mock_guild):
    """Create a mock Discord member."""

    class MockMember(mock_user.__class__):
        def __init__(self):
            super().__init__()
            self.guild = mock_guild

            # Mock guild permissions
            class MockPermissions:
                administrator = True

            self.guild_permissions = MockPermissions()

    return MockMember()


@pytest.fixture
def mock_context(mock_bot, mock_guild, mock_channel, mock_member):
    """Create a mock Discord context."""

    class MockContext:
        def __init__(self):
            self.bot = mock_bot
            self.guild = mock_guild
            self.channel = mock_channel
            self.author = mock_member
            self.message = MockMessage()
            self.command = None

        async def send(self, content=None, embed=None, file=None):
            return MockMessage()

        async def reply(self, content=None, embed=None, mention_author=True):
            return MockMessage()

        async def send_help(self, command=None):
            # Mock send_help for testing
            return MockMessage()

    class MockMessage:
        def __init__(self):
            self.id = 555555555
            self.reference = None
            self.attachments = []

    return MockContext()
