import pytest
from sqlalchemy import text

from app.database import (
    get_honeypot_db_manager,
    get_honeypot_session,
    get_real_db_manager,
    get_real_session,
    init_honeypot_db,
    init_real_db,
)


EXPECTED_TABLES = [
    "users",
    "customers",
    "products",
    "orders",
    "order_items",
    "payments",
]


@pytest.mark.asyncio
async def test_real_database_tables_exist():
    await init_real_db()

    async with get_real_session() as session:
        result = await session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' ORDER BY tablename"
            )
        )
        tables = [row.tablename for row in result.fetchall()]

    for table in EXPECTED_TABLES:
        assert table in tables, f"Table '{table}' not found in REAL database"


@pytest.mark.asyncio
async def test_honeypot_database_tables_exist():
    await init_honeypot_db()

    async with get_honeypot_session() as session:
        result = await session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' ORDER BY tablename"
            )
        )
        tables = [row.tablename for row in result.fetchall()]

    for table in EXPECTED_TABLES:
        assert table in tables, f"Table '{table}' not found in HONEYPOT database"


@pytest.mark.asyncio
async def test_real_database_has_data():
    async with get_real_session() as session:
        for table in EXPECTED_TABLES:
            result = await session.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            )
            count = result.scalar()

            assert count > 0, (
                f"Table '{table}' in REAL database is empty"
            )


@pytest.mark.asyncio
async def test_honeypot_database_has_data():
    async with get_honeypot_session() as session:
        for table in EXPECTED_TABLES:
            result = await session.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            )
            count = result.scalar()

            assert count > 0, (
                f"Table '{table}' in HONEYPOT database is empty"
            )


@pytest.mark.asyncio
async def test_real_and_honeypot_data_is_different():
    real_manager = get_real_db_manager()
    honeypot_manager = get_honeypot_db_manager()

    async with (
        real_manager.session() as real_session,
        honeypot_manager.session() as hp_session,
    ):
        for table in EXPECTED_TABLES:
            real_result = await real_session.execute(
                text(f"SELECT * FROM {table} ORDER BY id")
            )
            hp_result = await hp_session.execute(
                text(f"SELECT * FROM {table} ORDER BY id")
            )

            real_rows = real_result.fetchall()
            hp_rows = hp_result.fetchall()

            assert len(real_rows) > 0, (
                f"REAL {table} should have data"
            )
            assert len(hp_rows) > 0, (
                f"HONEYPOT {table} should have data"
            )

            if table == "users":
                real_emails = {row.email for row in real_rows}
                hp_emails = {row.email for row in hp_rows}

                assert real_emails != hp_emails, (
                    "User emails should differ between databases"
                )
                assert not real_emails & hp_emails, (
                    "No email overlap between databases"
                )

            elif table == "customers":
                real_emails = {row.email for row in real_rows}
                hp_emails = {row.email for row in hp_rows}

                assert real_emails != hp_emails, (
                    "Customer emails should differ between databases"
                )
                assert not real_emails & hp_emails, (
                    "No email overlap between databases"
                )

            elif table == "products":
                real_skus = {row.sku for row in real_rows}
                hp_skus = {row.sku for row in hp_rows}

                assert real_skus != hp_skus, (
                    "Product SKUs should differ between databases"
                )
                assert not real_skus & hp_skus, (
                    "No SKU overlap between databases"
                )

            elif table == "orders":
                real_order_nums = {
                    row.order_number for row in real_rows
                }
                hp_order_nums = {
                    row.order_number for row in hp_rows
                }

                assert real_order_nums != hp_order_nums, (
                    "Order numbers should differ between databases"
                )
                assert not real_order_nums & hp_order_nums, (
                    "No order number overlap between databases"
                )


@pytest.mark.asyncio
async def test_real_database_specific_data():
    async with get_real_session() as session:
        result = await session.execute(
            text(
                "SELECT email FROM users "
                "WHERE username = 'admin'"
            )
        )
        row = result.fetchone()

        assert row is not None
        assert row.email == "admin@phantomlayer.demo"

        result = await session.execute(
            text(
                "SELECT sku FROM products "
                "WHERE name LIKE 'PhantomLayer%'"
            )
        )
        skus = {row.sku for row in result.fetchall()}

        assert "PL-LAPTOP-001" in skus
        assert "PL-MONITOR-001" in skus

        result = await session.execute(
            text(
                "SELECT order_number FROM orders "
                "WHERE customer_id = ("
                "SELECT id FROM customers "
                "WHERE email = 'alice.johnson@email.com'"
                ")"
            )
        )
        order_nums = {
            row.order_number for row in result.fetchall()
        }

        assert "ORD-2024-0001" in order_nums


@pytest.mark.asyncio
async def test_honeypot_database_specific_data():
    async with get_honeypot_session() as session:
        result = await session.execute(
            text(
                "SELECT email FROM users "
                "WHERE username = 'sysadmin'"
            )
        )
        row = result.fetchone()

        assert row is not None
        assert row.email == "sysadmin@deception.local"

        result = await session.execute(
            text(
                "SELECT sku FROM products "
                "WHERE name LIKE 'Honeypot%'"
            )
        )
        skus = {row.sku for row in result.fetchall()}

        assert "HP-SERVER-001" in skus
        assert "HP-STORAGE-001" in skus

        result = await session.execute(
            text(
                "SELECT order_number FROM orders "
                "WHERE customer_id = ("
                "SELECT id FROM customers "
                "WHERE email = 'james.anderson@corp.example'"
                ")"
            )
        )
        order_nums = {
            row.order_number for row in result.fetchall()
        }

        assert "HPD-2024-0001" in order_nums


@pytest.mark.asyncio
async def test_databases_are_independent():
    real_manager = get_real_db_manager()
    honeypot_manager = get_honeypot_db_manager()

    assert real_manager is not honeypot_manager
    assert real_manager.database_url != honeypot_manager.database_url

    from app.config import settings
    assert real_manager.database_url == settings.real_database_url
    assert honeypot_manager.database_url == settings.honeypot_database_url

    async with (
        real_manager.session() as real_session,
        honeypot_manager.session() as hp_session,
    ):
        real_result = await real_session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' ORDER BY tablename"
            )
        )
        hp_result = await hp_session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' ORDER BY tablename"
            )
        )

        real_tables = [
            row.tablename for row in real_result.fetchall()
        ]
        hp_tables = [
            row.tablename for row in hp_result.fetchall()
        ]

        assert set(real_tables) == set(hp_tables) == set(EXPECTED_TABLES)


@pytest.mark.asyncio
async def test_foreign_key_relationships_real():
    async with get_real_session() as session:
        result = await session.execute(
            text(
                """
                SELECT o.order_number, c.email
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                WHERE c.email = 'alice.johnson@email.com'
                """
            )
        )

        rows = result.fetchall()

        assert len(rows) >= 1
        assert rows[0].order_number == "ORD-2024-0001"

        result = await session.execute(
            text(
                """
                SELECT oi.quantity, p.name
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN orders o ON oi.order_id = o.id
                WHERE o.order_number = 'ORD-2024-0001'
                """
            )
        )

        rows = result.fetchall()

        assert len(rows) == 1
        assert rows[0].name == "PhantomLayer Laptop Pro 15"


@pytest.mark.asyncio
async def test_foreign_key_relationships_honeypot():
    async with get_honeypot_session() as session:
        result = await session.execute(
            text(
                """
                SELECT o.order_number, c.email
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                WHERE c.email = 'james.anderson@corp.example'
                """
            )
        )

        rows = result.fetchall()

        assert len(rows) >= 1
        assert rows[0].order_number == "HPD-2024-0001"

        result = await session.execute(
            text(
                """
                SELECT oi.quantity, p.name
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN orders o ON oi.order_id = o.id
                WHERE o.order_number = 'HPD-2024-0001'
                """
            )
        )

        rows = result.fetchall()

        assert len(rows) == 1
        assert rows[0].name == "Honeypot Deception Appliance"