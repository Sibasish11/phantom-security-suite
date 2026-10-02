import asyncio
import sys

from app.database import (
    close_db_connections,
    get_control_db_manager,
    get_honeypot_db_manager,
    get_real_db_manager,
    init_control_db,
    init_honeypot_db,
    init_real_db,
)
# Import declarative modules so ControlBase metadata includes every control
# plane table before create_all (including durable security records and the
# trusted integration decision ledger).
from app import models as _models  # noqa: F401
from app.integrations import models as _integration_models  # noqa: F401
from app.seed import seed_honeypot_database, seed_real_database


async def init_and_seed_real() -> None:
    print("Initializing REAL database...")
    manager = get_real_db_manager()

    await init_real_db()

    print("REAL database schema created.")

    print("Seeding REAL database...")
    async with manager.session() as session:
        await seed_real_database(session)

    print("REAL database seeded successfully.")


async def init_and_seed_honeypot() -> None:
    print("Initializing HONEYPOT database...")
    manager = get_honeypot_db_manager()

    await init_honeypot_db()

    print("HONEYPOT database schema created.")

    print("Seeding HONEYPOT database...")
    async with manager.session() as session:
        await seed_honeypot_database(session)

    print("HONEYPOT database seeded successfully.")


async def init_control() -> None:
    print("Initializing CONTROL database...")
    manager = get_control_db_manager()

    await init_control_db()

    print("CONTROL database schema created.")
    print("CONTROL database initialization complete.")


async def init_and_seed_all() -> None:
    await init_and_seed_real()
    await init_and_seed_honeypot()
    await init_control()


async def drop_real() -> None:
    print("Dropping REAL database tables...")
    manager = get_real_db_manager()

    await manager.drop_tables()

    print("REAL database tables dropped.")


async def drop_honeypot() -> None:
    print("Dropping HONEYPOT database tables...")
    manager = get_honeypot_db_manager()

    await manager.drop_tables()

    print("HONEYPOT database tables dropped.")


async def drop_control() -> None:
    print("Dropping CONTROL database tables...")
    manager = get_control_db_manager()

    await manager.drop_tables()

    print("CONTROL database tables dropped.")


async def drop_all() -> None:
    await drop_real()
    await drop_honeypot()
    await drop_control()


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m app.init_db [command]")
        print()
        print("Commands:")
        print("  init-real       Initialize and seed REAL database")
        print("  init-honeypot   Initialize and seed HONEYPOT database")
        print("  init-control    Initialize CONTROL database")
        print("  init-all        Initialize all databases")
        print("  drop-real       Drop REAL database tables")
        print("  drop-honeypot   Drop HONEYPOT database tables")
        print("  drop-control    Drop CONTROL database tables")
        print("  drop-all        Drop all database tables")
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "init-real":
            await init_and_seed_real()

        elif command == "init-honeypot":
            await init_and_seed_honeypot()

        elif command == "init-control":
            await init_control()

        elif command == "init-all":
            await init_and_seed_all()

        elif command == "drop-real":
            await drop_real()

        elif command == "drop-honeypot":
            await drop_honeypot()

        elif command == "drop-control":
            await drop_control()

        elif command == "drop-all":
            await drop_all()

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    finally:
        await close_db_connections()


if __name__ == "__main__":
    asyncio.run(main())