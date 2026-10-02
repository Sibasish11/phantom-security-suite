"""Isolate legacy integration tests in dedicated QA databases.

Invoked only by scripts/test-backend.sh. The fixture database is seeded
idempotently; application schema/data databases are not dropped or cleared.
"""

import asyncio
import os
import sys

from sqlalchemy import make_url, select


def main() -> int:
    if os.environ.get("PHANTOMLAYER_TEST_DATABASES") != "1":
        raise RuntimeError("Use scripts/test-backend.sh to run database tests safely")

    suffix = os.environ.get("PHANTOMLAYER_QA_DATABASE_SUFFIX", "")
    if not suffix or not suffix.replace("_", "").isalnum():
        raise RuntimeError("QA database suffix is missing or unsafe")
    names = {
        "REAL_DATABASE_URL": f"phantomlayer_qa_real_{suffix}",
        "HONEYPOT_DATABASE_URL": f"phantomlayer_qa_honeypot_{suffix}",
        "CONTROL_DATABASE_URL": f"phantomlayer_qa_control_{suffix}",
    }
    for variable, database in names.items():
        url = make_url(os.environ[variable]).set(database=database)
        os.environ[variable] = url.render_as_string(hide_password=False)

    from app import models  # noqa: F401
    from app.integrations import models as integration_models  # noqa: F401
    from app.database import (
        Base, ControlBase, get_sync_control_db_manager,
        get_real_db_manager, get_honeypot_db_manager, close_db_connections,
    )
    from app.models.schema import User
    from app.models.control_plane import Organization, OrganizationUser, OrganizationRole
    from app.auth.security import hash_password
    from app.seed import seed_real_database, seed_honeypot_database

    async def prepare():
        for manager, seed in (
            (get_real_db_manager(), seed_real_database),
            (get_honeypot_db_manager(), seed_honeypot_database),
        ):
            await manager.create_tables()
            async with manager.session() as session:
                if (await session.execute(select(User.id).limit(1))).first() is None:
                    await seed(session)

        control = get_sync_control_db_manager()
        control.create_tables(ControlBase.metadata)
        with control.session() as session:
            user = session.execute(select(OrganizationUser).where(
                OrganizationUser.email == "login-test@example.com"
            )).scalar_one_or_none()
            if user is None:
                org = Organization(name="QA fixture organization", slug="qa-fixture")
                session.add(org)
                session.flush()
                session.add(OrganizationUser(
                    organization_id=org.id,
                    email="login-test@example.com",
                    password_hash=hash_password("TestPassword123!"),
                    full_name="QA Administrator",
                    role=OrganizationRole.ADMIN,
                ))
                session.commit()
        await close_db_connections()

    asyncio.run(prepare())
    import pytest
    return pytest.main(["-p", "no:cacheprovider", *(sys.argv[1:] or ["-q"])])


if __name__ == "__main__":
    raise SystemExit(main())
