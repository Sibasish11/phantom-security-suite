from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


class LocalDatabaseGateway:
    def __init__(
        self,
        *,
        real_database_url: str,
        honeypot_database_url: str,
    ):
        self.real_database_url = real_database_url
        self.honeypot_database_url = honeypot_database_url

    def _url_for_target(self, target: str) -> str:
        if target == "real":
            return self.real_database_url

        if target == "honeypot":
            return self.honeypot_database_url

        raise ValueError(f"Unknown database target: {target}")

    async def execute(
        self,
        *,
        target: str,
        operation: str,
        parameters: dict[str, Any],
    ) -> Any:
        database_url = self._url_for_target(target)

        engine = create_async_engine(
            database_url,
            pool_pre_ping=True,
        )

        try:
            async with engine.connect() as connection:
                return await self._execute_operation(
                    connection=connection,
                    operation=operation,
                    parameters=parameters,
                )
        finally:
            await engine.dispose()

    async def health_check(self, target: str) -> bool:
        database_url = self._url_for_target(target)

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

    async def _execute_operation(
        self,
        *,
        connection,
        operation: str,
        parameters: dict[str, Any],
    ) -> Any:
        if operation == "health_check":
            result = await connection.execute(
                text("SELECT 1 AS health")
            )

            return [
                dict(row._mapping)
                for row in result.fetchall()
            ]

        if operation == "list_tables":
            result = await connection.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                    """
                )
            )

            return [
                dict(row._mapping)
                for row in result.fetchall()
            ]

        if operation in {
            "get_users",
            "get_customers",
            "get_products",
            "get_orders",
        }:
            table = {
                "get_users": "users",
                "get_customers": "customers",
                "get_products": "products",
                "get_orders": "orders",
            }[operation]

            limit = min(
                max(
                    int(parameters.get("limit", 50)),
                    1,
                ),
                100,
            )

            offset = max(
                int(parameters.get("offset", 0)),
                0,
            )

            result = await connection.execute(
                text(
                    f"""
                    SELECT *
                    FROM {table}
                    LIMIT :limit
                    OFFSET :offset
                    """
                ),
                {
                    "limit": limit,
                    "offset": offset,
                },
            )

            return [
                dict(row._mapping)
                for row in result.fetchall()
            ]

        if operation == "get_customer":
            customer_id = parameters.get("id")

            if customer_id is None:
                raise ValueError(
                    "get_customer requires 'id'"
                )

            result = await connection.execute(
                text(
                    """
                    SELECT *
                    FROM customers
                    WHERE id = :id
                    LIMIT 1
                    """
                ),
                {"id": customer_id},
            )

            row = result.fetchone()

            return (
                dict(row._mapping)
                if row is not None
                else {}
            )

        if operation == "get_user":
            user_id = parameters.get("id")

            if user_id is None:
                raise ValueError(
                    "get_user requires 'id'"
                )

            result = await connection.execute(
                text(
                    """
                    SELECT *
                    FROM users
                    WHERE id = :id
                    LIMIT 1
                    """
                ),
                {"id": user_id},
            )

            row = result.fetchone()

            return (
                dict(row._mapping)
                if row is not None
                else {}
            )

        if operation == "get_order":
            order_id = parameters.get("id")

            if order_id is None:
                raise ValueError(
                    "get_order requires 'id'"
                )

            result = await connection.execute(
                text(
                    """
                    SELECT *
                    FROM orders
                    WHERE id = :id
                    LIMIT 1
                    """
                ),
                {"id": order_id},
            )

            row = result.fetchone()

            return (
                dict(row._mapping)
                if row is not None
                else {}
            )

        raise ValueError(
            f"Unsupported operation: {operation}"
        )