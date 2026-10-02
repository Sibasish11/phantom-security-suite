from typing import Any, Optional
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_honeypot_session, get_real_session
from app.gateway.schemas import GatewayOperation, GatewayRequest, GatewayResponse, GatewayTarget


class GatewayService:
    def __init__(self):
        pass

    async def _get_session(self, target: GatewayTarget):
        if target == GatewayTarget.REAL:
            return get_real_session()
        elif target == GatewayTarget.HONEYPOT:
            return get_honeypot_session()
        else:
            raise ValueError(f"Unknown target: {target}")

    def _serialize_row(self, row) -> dict[str, Any]:
        if row is None:
            return {}
        return {column: getattr(row, column) for column in row._fields}

    async def execute(self, request: GatewayRequest) -> GatewayResponse:
        try:
            for key, ceiling in (("limit", 1000), ("offset", 100000)):
                value = (request.parameters or {}).get(key, 50 if key == 'limit' else 0)
                if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= ceiling:
                    raise ValueError('Invalid pagination')
            async with await self._get_session(request.target) as session:
                data = await self._execute_operation(session, request.operation, request.parameters or {})
                row_count = len(data) if isinstance(data, list) else (1 if data else 0)
                return GatewayResponse(
                    target=request.target,
                    operation=request.operation,
                    success=True,
                    data=data,
                    row_count=row_count,
                )
        except Exception as e:
            logging.getLogger(__name__).warning('gateway_operation_failed operation=%s error_type=%s', request.operation.value, type(e).__name__)
            return GatewayResponse(
                target=request.target,
                operation=request.operation,
                success=False,
                error='Invalid operation parameters' if isinstance(e, (ValueError, TypeError)) else 'Database operation unavailable',
            )

    async def _execute_operation(
        self,
        session: AsyncSession,
        operation: GatewayOperation,
        parameters: dict[str, Any],
    ) -> Any:
        if operation == GatewayOperation.HEALTH_CHECK:
            result = await session.execute(text("SELECT 1 as health"))
            row = result.fetchone()
            return [{"health": row[0] if row else 0}]

        elif operation == GatewayOperation.LIST_TABLES:
            result = await session.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
            )
            return [{"table": row.tablename} for row in result.fetchall()]

        elif operation == GatewayOperation.GET_USERS:
            limit = parameters.get("limit", 50)
            offset = parameters.get("offset", 0)
            result = await session.execute(
                text("SELECT id, username, email, role, is_active, created_at FROM users ORDER BY id LIMIT :limit OFFSET :offset"),
                {"limit": limit, "offset": offset},
            )
            return [self._serialize_row(row) for row in result.fetchall()]

        elif operation == GatewayOperation.GET_CUSTOMERS:
            limit = parameters.get("limit", 50)
            offset = parameters.get("offset", 0)
            result = await session.execute(
                text("SELECT id, email, first_name, last_name, city, state, country, is_active FROM customers ORDER BY id LIMIT :limit OFFSET :offset"),
                {"limit": limit, "offset": offset},
            )
            return [self._serialize_row(row) for row in result.fetchall()]

        elif operation == GatewayOperation.GET_PRODUCTS:
            limit = parameters.get("limit", 50)
            offset = parameters.get("offset", 0)
            result = await session.execute(
                text("SELECT id, sku, name, price, cost, stock_quantity, is_active FROM products ORDER BY id LIMIT :limit OFFSET :offset"),
                {"limit": limit, "offset": offset},
            )
            return [self._serialize_row(row) for row in result.fetchall()]

        elif operation == GatewayOperation.GET_ORDERS:
            limit = parameters.get("limit", 50)
            offset = parameters.get("offset", 0)
            customer_id = parameters.get("customer_id")
            if customer_id is not None:
                result = await session.execute(
                    text("SELECT id, order_number, customer_id, status, total_amount, created_at FROM orders WHERE customer_id = :customer_id ORDER BY id LIMIT :limit OFFSET :offset"),
                    {"customer_id": int(customer_id), "limit": limit, "offset": offset},
                )
            else:
                result = await session.execute(
                    text("SELECT id, order_number, customer_id, status, total_amount, created_at FROM orders ORDER BY id LIMIT :limit OFFSET :offset"),
                    {"limit": limit, "offset": offset},
                )
            return [self._serialize_row(row) for row in result.fetchall()]

        elif operation == GatewayOperation.GET_CUSTOMER:
            customer_id = parameters.get("id") or parameters.get("customer_id")
            email = parameters.get("email")
            if customer_id is not None:
                result = await session.execute(
                    text("SELECT id, email, first_name, last_name, phone, address_line1, address_line2, city, state, postal_code, country, assigned_user_id, is_active, created_at FROM customers WHERE id = :id"),
                    {"id": int(customer_id)},
                )
            elif email:
                result = await session.execute(
                    text("SELECT id, email, first_name, last_name, phone, address_line1, address_line2, city, state, postal_code, country, assigned_user_id, is_active, created_at FROM customers WHERE email = :email"),
                    {"email": email},
                )
            else:
                return []
            return [self._serialize_row(row) for row in result.fetchall()]

        elif operation == GatewayOperation.GET_ORDER:
            order_id = parameters.get("id") or parameters.get("order_id")
            order_number = parameters.get("order_number")
            if order_id is not None:
                order_result = await session.execute(
                    text("SELECT id, order_number, customer_id, status, subtotal, tax_amount, shipping_amount, total_amount, notes, created_at FROM orders WHERE id = :id"),
                    {"id": int(order_id)},
                )
            elif order_number:
                order_result = await session.execute(
                    text("SELECT id, order_number, customer_id, status, subtotal, tax_amount, shipping_amount, total_amount, notes, created_at FROM orders WHERE order_number = :order_number"),
                    {"order_number": str(order_number)},
                )
            else:
                return []

            order_row = order_result.fetchone()
            if not order_row:
                return []

            order_data = self._serialize_row(order_row)
            actual_order_id = order_data["id"]

            items_result = await session.execute(
                text("""
                    SELECT oi.id, oi.order_id, oi.product_id, oi.quantity, oi.unit_price, oi.total_price,
                           p.sku as product_sku, p.name as product_name
                    FROM order_items oi
                    JOIN products p ON oi.product_id = p.id
                    WHERE oi.order_id = :order_id
                    ORDER BY oi.id
                """),
                {"order_id": actual_order_id},
            )
            order_data["items"] = [self._serialize_row(r) for r in items_result.fetchall()]

            payments_result = await session.execute(
                text("SELECT id, order_id, payment_method, status, amount, transaction_id, processed_at FROM payments WHERE order_id = :order_id"),
                {"order_id": actual_order_id},
            )
            order_data["payments"] = [self._serialize_row(r) for r in payments_result.fetchall()]
            return [order_data]

        elif operation == GatewayOperation.GET_USER:
            user_id = parameters.get("id") or parameters.get("user_id")
            username = parameters.get("username")
            if user_id is not None:
                result = await session.execute(
                    text("SELECT id, username, email, role, is_active, created_at FROM users WHERE id = :id"),
                    {"id": int(user_id)},
                )
            elif username:
                result = await session.execute(
                    text("SELECT id, username, email, role, is_active, created_at FROM users WHERE username = :username"),
                    {"username": str(username)},
                )
            else:
                return []
            return [self._serialize_row(row) for row in result.fetchall()]

        else:
            raise ValueError(f"Unsupported operation: {operation}")


    async def health_check(self) -> dict[str, str]:
        real_status = "unknown"
        honeypot_status = "unknown"

        try:
            async with get_real_session() as session:
                result = await session.execute(text("SELECT 1"))
                real_status = "healthy" if result.fetchone() else "unhealthy"
        except Exception:
            real_status = "unhealthy"

        try:
            async with get_honeypot_session() as session:
                result = await session.execute(text("SELECT 1"))
                honeypot_status = "healthy" if result.fetchone() else "unhealthy"
        except Exception:
            honeypot_status = "unhealthy"

        return {
            "real_database": real_status,
            "honeypot_database": honeypot_status,
        }


gateway_service = GatewayService()