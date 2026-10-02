from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


class ControlBase(DeclarativeBase):
    pass


class DatabaseManager:
    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        metadata=None,
    ):
        self.database_url = database_url
        self.echo = echo
        self.metadata = metadata or Base.metadata
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_async_engine(
                self.database_url,
                echo=self.echo,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(self.metadata.create_all)

    async def drop_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(self.metadata.drop_all)

    async def dispose(self) -> None:
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


class SyncDatabaseManager:
    """
    Synchronous SQLAlchemy database manager.

    Used by the existing synchronous control-plane service contracts.
    It points at the same PostgreSQL control database as DatabaseManager.
    """

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
    ):
        self.database_url = database_url
        self.echo = echo
        self._engine: Engine | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(
                self.database_url,
                echo=self.echo,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
        return self._engine

    def session(self) -> Session:
        return Session(
            self.engine,
            expire_on_commit=False,
            autoflush=False,
        )

    def create_tables(self, metadata) -> None:
        metadata.create_all(self.engine)

    def drop_tables(self, metadata) -> None:
        metadata.drop_all(self.engine)

    def dispose(self) -> None:
        if self._engine:
            self._engine.dispose()
            self._engine = None


_real_db_manager: DatabaseManager | None = None
_honeypot_db_manager: DatabaseManager | None = None
_control_db_manager: DatabaseManager | None = None
_sync_control_db_manager: SyncDatabaseManager | None = None


def get_real_db_manager() -> DatabaseManager:
    global _real_db_manager

    if _real_db_manager is None:
        _real_db_manager = DatabaseManager(
            database_url=settings.real_database_url,
            echo=settings.debug,
            metadata=Base.metadata,
        )

    return _real_db_manager


def get_honeypot_db_manager() -> DatabaseManager:
    global _honeypot_db_manager

    if _honeypot_db_manager is None:
        _honeypot_db_manager = DatabaseManager(
            database_url=settings.honeypot_database_url,
            echo=settings.debug,
            metadata=Base.metadata,
        )

    return _honeypot_db_manager


def get_control_db_manager() -> DatabaseManager:
    global _control_db_manager

    if _control_db_manager is None:
        _control_db_manager = DatabaseManager(
            database_url=settings.control_database_url,
            echo=settings.debug,
            metadata=ControlBase.metadata,
        )

    return _control_db_manager


def get_sync_control_db_manager() -> SyncDatabaseManager:
    global _sync_control_db_manager

    if _sync_control_db_manager is None:
        _sync_control_db_manager = SyncDatabaseManager(
            database_url=settings.control_database_url,
            echo=settings.debug,
        )

    return _sync_control_db_manager


@asynccontextmanager
async def get_real_session() -> AsyncGenerator[AsyncSession, None]:
    manager = get_real_db_manager()

    async with manager.session() as session:
        yield session


@asynccontextmanager
async def get_honeypot_session() -> AsyncGenerator[AsyncSession, None]:
    manager = get_honeypot_db_manager()

    async with manager.session() as session:
        yield session


@asynccontextmanager
async def get_control_session() -> AsyncGenerator[AsyncSession, None]:
    manager = get_control_db_manager()

    async with manager.session() as session:
        yield session


async def init_real_db() -> None:
    manager = get_real_db_manager()
    await manager.create_tables()


async def init_honeypot_db() -> None:
    manager = get_honeypot_db_manager()
    await manager.create_tables()


async def init_control_db() -> None:
    manager = get_control_db_manager()
    await manager.create_tables()


async def close_db_connections() -> None:
    global _real_db_manager
    global _honeypot_db_manager
    global _control_db_manager
    global _sync_control_db_manager

    if _real_db_manager:
        await _real_db_manager.dispose()
        _real_db_manager = None

    if _honeypot_db_manager:
        await _honeypot_db_manager.dispose()
        _honeypot_db_manager = None

    if _control_db_manager:
        await _control_db_manager.dispose()
        _control_db_manager = None

    if _sync_control_db_manager:
        _sync_control_db_manager.dispose()
        _sync_control_db_manager = None