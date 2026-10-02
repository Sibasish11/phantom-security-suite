from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def check_database(database_url: str) -> bool:
    if not database_url:
        return False

    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
    )

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

        return True

    except Exception:
        return False

    finally:
        await engine.dispose()


async def check_databases(
    real_database_url: str,
    honeypot_database_url: str,
) -> tuple[bool, bool]:
    real_reachable = await check_database(real_database_url)
    honeypot_reachable = await check_database(honeypot_database_url)

    return real_reachable, honeypot_reachable