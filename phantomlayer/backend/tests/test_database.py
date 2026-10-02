import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    get_honeypot_db_manager,
    get_honeypot_session,
    get_real_db_manager,
    get_real_session,
    init_honeypot_db,
    init_real_db,
)


from app.config import settings

REAL_DATABASE_URL = settings.real_database_url
HONEYPOT_DATABASE_URL = settings.honeypot_database_url


@pytest.mark.asyncio
async def test_real_database_config_initialization():
    manager = get_real_db_manager()

    assert manager is not None
    assert manager.database_url == REAL_DATABASE_URL


@pytest.mark.asyncio
async def test_honeypot_database_config_initialization():
    manager = get_honeypot_db_manager()

    assert manager is not None
    assert manager.database_url == HONEYPOT_DATABASE_URL


@pytest.mark.asyncio
async def test_real_database_connection():
    async with get_real_session() as session:
        assert isinstance(session, AsyncSession)

        result = await session.execute(
            text("SELECT 1 as test")
        )

        row = result.fetchone()

        assert row is not None
        assert row.test == 1


@pytest.mark.asyncio
async def test_honeypot_database_connection():
    async with get_honeypot_session() as session:
        assert isinstance(session, AsyncSession)

        result = await session.execute(
            text("SELECT 1 as test")
        )

        row = result.fetchone()

        assert row is not None
        assert row.test == 1


@pytest.mark.asyncio
async def test_real_database_create_tables():
    await init_real_db()

    async with get_real_session() as session:
        result = await session.execute(
            text(
                "SELECT tablename "
                "FROM pg_tables "
                "WHERE schemaname = 'public'"
            )
        )

        tables = [
            row.tablename
            for row in result.fetchall()
        ]

        assert isinstance(tables, list)


@pytest.mark.asyncio
async def test_honeypot_database_create_tables():
    await init_honeypot_db()

    async with get_honeypot_session() as session:
        result = await session.execute(
            text(
                "SELECT tablename "
                "FROM pg_tables "
                "WHERE schemaname = 'public'"
            )
        )

        tables = [
            row.tablename
            for row in result.fetchall()
        ]

        assert isinstance(tables, list)


@pytest.mark.asyncio
async def test_databases_are_independent():
    real_manager = get_real_db_manager()
    honeypot_manager = get_honeypot_db_manager()

    assert real_manager is not honeypot_manager

    assert (
        real_manager.database_url
        != honeypot_manager.database_url
    )

    assert (
        real_manager.database_url
        == REAL_DATABASE_URL
    )

    assert (
        honeypot_manager.database_url
        == HONEYPOT_DATABASE_URL
    )