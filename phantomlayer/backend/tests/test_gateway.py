import pytest
from fastapi.testclient import TestClient

from app.gateway.schemas import GatewayOperation, GatewayRequest, GatewayTarget
from app.gateway.service import gateway_service
from app.main import app


@pytest.fixture
def client(authenticated_client):
    return authenticated_client


def test_gateway_service_initializes():
    assert gateway_service is not None


def test_gateway_request_schema_real():
    request = GatewayRequest(
        target=GatewayTarget.REAL,
        operation=GatewayOperation.GET_PRODUCTS,
    )

    assert request.target == GatewayTarget.REAL
    assert request.operation == GatewayOperation.GET_PRODUCTS


def test_gateway_request_schema_honeypot():
    request = GatewayRequest(
        target=GatewayTarget.HONEYPOT,
        operation=GatewayOperation.GET_PRODUCTS,
    )

    assert request.target == GatewayTarget.HONEYPOT
    assert request.operation == GatewayOperation.GET_PRODUCTS


@pytest.mark.asyncio
async def test_gateway_service_real_products():
    result = await gateway_service.execute(
        GatewayRequest(
            target=GatewayTarget.REAL,
            operation=GatewayOperation.GET_PRODUCTS,
        )
    )

    assert result.success is True
    assert result.target == GatewayTarget.REAL
    assert result.operation == GatewayOperation.GET_PRODUCTS
    assert result.data is not None
    assert result.row_count is not None


@pytest.mark.asyncio
async def test_gateway_service_honeypot_products():
    result = await gateway_service.execute(
        GatewayRequest(
            target=GatewayTarget.HONEYPOT,
            operation=GatewayOperation.GET_PRODUCTS,
        )
    )

    assert result.success is True
    assert result.target == GatewayTarget.HONEYPOT
    assert result.operation == GatewayOperation.GET_PRODUCTS
    assert result.data is not None
    assert result.row_count is not None


@pytest.mark.asyncio
async def test_gateway_service_real_vs_honeypot_different():
    real_result = await gateway_service.execute(
        GatewayRequest(
            target=GatewayTarget.REAL,
            operation=GatewayOperation.GET_PRODUCTS,
        )
    )

    honeypot_result = await gateway_service.execute(
        GatewayRequest(
            target=GatewayTarget.HONEYPOT,
            operation=GatewayOperation.GET_PRODUCTS,
        )
    )

    assert real_result.success is True
    assert honeypot_result.success is True
    assert real_result.data != honeypot_result.data


@pytest.mark.asyncio
async def test_gateway_service_get_users_real():
    result = await gateway_service.execute(
        GatewayRequest(
            target=GatewayTarget.REAL,
            operation=GatewayOperation.GET_USERS,
        )
    )

    assert result.success is True
    assert result.target == GatewayTarget.REAL
    assert result.operation == GatewayOperation.GET_USERS
    assert isinstance(result.data, list)


@pytest.mark.asyncio
async def test_gateway_service_get_users_honeypot():
    result = await gateway_service.execute(
        GatewayRequest(
            target=GatewayTarget.HONEYPOT,
            operation=GatewayOperation.GET_USERS,
        )
    )

    assert result.success is True
    assert result.target == GatewayTarget.HONEYPOT
    assert result.operation == GatewayOperation.GET_USERS
    assert isinstance(result.data, list)


@pytest.mark.asyncio
async def test_gateway_service_list_tables_real():
    result = await gateway_service.execute(
        GatewayRequest(
            target=GatewayTarget.REAL,
            operation=GatewayOperation.LIST_TABLES,
        )
    )

    assert result.success is True
    assert result.target == GatewayTarget.REAL
    assert result.operation == GatewayOperation.LIST_TABLES
    assert isinstance(result.data, list)


@pytest.mark.asyncio
async def test_gateway_service_list_tables_honeypot():
    result = await gateway_service.execute(
        GatewayRequest(
            target=GatewayTarget.HONEYPOT,
            operation=GatewayOperation.LIST_TABLES,
        )
    )

    assert result.success is True
    assert result.target == GatewayTarget.HONEYPOT
    assert result.operation == GatewayOperation.LIST_TABLES
    assert isinstance(result.data, list)


@pytest.mark.asyncio
async def test_gateway_service_get_customers_real():
    result = await gateway_service.execute(
        GatewayRequest(
            target=GatewayTarget.REAL,
            operation=GatewayOperation.GET_CUSTOMERS,
        )
    )

    assert result.success is True
    assert result.target == GatewayTarget.REAL
    assert result.operation == GatewayOperation.GET_CUSTOMERS
    assert isinstance(result.data, list)


@pytest.mark.asyncio
async def test_gateway_service_get_customers_honeypot():
    result = await gateway_service.execute(
        GatewayRequest(
            target=GatewayTarget.HONEYPOT,
            operation=GatewayOperation.GET_CUSTOMERS,
        )
    )

    assert result.success is True
    assert result.target == GatewayTarget.HONEYPOT
    assert result.operation == GatewayOperation.GET_CUSTOMERS
    assert isinstance(result.data, list)


@pytest.mark.asyncio
async def test_gateway_service_get_orders_real():
    result = await gateway_service.execute(
        GatewayRequest(
            target=GatewayTarget.REAL,
            operation=GatewayOperation.GET_ORDERS,
        )
    )

    assert result.success is True
    assert result.target == GatewayTarget.REAL
    assert result.operation == GatewayOperation.GET_ORDERS
    assert isinstance(result.data, list)


@pytest.mark.asyncio
async def test_gateway_service_get_orders_honeypot():
    result = await gateway_service.execute(
        GatewayRequest(
            target=GatewayTarget.HONEYPOT,
            operation=GatewayOperation.GET_ORDERS,
        )
    )

    assert result.success is True
    assert result.target == GatewayTarget.HONEYPOT
    assert result.operation == GatewayOperation.GET_ORDERS
    assert isinstance(result.data, list)


def test_gateway_query_endpoint_real(client):
    response = client.post(
        "/gateway/query",
        json={
            "target": "real",
            "operation": "get_products",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["original_target"] == "real"
    assert data["operation"] == "get_products"
    assert data["final_target"] == "real"
    assert "risk_score" in data
    assert "suspicious" in data
    assert "routing_decision" in data
    assert "gateway_result" in data

    assert data["gateway_success"] is True
    assert data["gateway_result"] is not None


def test_gateway_query_endpoint_honeypot(client):
    response = client.post(
        "/gateway/query",
        json={
            "target": "honeypot",
            "operation": "get_products",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["original_target"] == "honeypot"
    assert data["operation"] == "get_products"
    assert data["final_target"] == "honeypot"
    assert "risk_score" in data
    assert "suspicious" in data
    assert "routing_decision" in data
    assert "gateway_result" in data

    assert data["gateway_success"] is True
    assert data["gateway_result"] is not None


def test_gateway_query_real_vs_honeypot_different(client):
    real_response = client.post(
        "/gateway/query",
        json={
            "target": "real",
            "operation": "get_products",
        },
    )

    honeypot_response = client.post(
        "/gateway/query",
        json={
            "target": "honeypot",
            "operation": "get_products",
        },
    )

    assert real_response.status_code == 200
    assert honeypot_response.status_code == 200

    real_data = real_response.json()
    honeypot_data = honeypot_response.json()

    assert real_data["gateway_success"] is True
    assert honeypot_data["gateway_success"] is True

    assert (
        real_data["gateway_result"]
        != honeypot_data["gateway_result"]
    )


def test_gateway_query_list_tables(client):
    response = client.post(
        "/gateway/query",
        json={
            "target": "real",
            "operation": "list_tables",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["operation"] == "list_tables"
    assert data["final_target"] == "honeypot"
    assert data["gateway_success"] is True


def test_gateway_query_sensitive_operation_routes_honeypot(client):
    response = client.post(
        "/gateway/query",
        json={
            "target": "real",
            "operation": "get_customers",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["original_target"] == "real"
    assert data["operation"] == "get_customers"
    assert data["final_target"] == "honeypot"
    assert data["suspicious"] is True
    assert data["gateway_success"] is True


def test_gateway_query_invalid_target(client):
    response = client.post(
        "/gateway/query",
        json={
            "target": "invalid",
            "operation": "get_users",
        },
    )

    assert response.status_code == 422


def test_gateway_query_invalid_operation(client):
    response = client.post(
        "/gateway/query",
        json={
            "target": "real",
            "operation": "drop_table",
        },
    )

    assert response.status_code == 422


def test_gateway_health_endpoint(client):
    response = client.get("/gateway/health")

    assert response.status_code == 200

    data = response.json()

    assert data["gateway"] == "PhantomLayer Gateway"
    assert data["status"] == "healthy"
    assert data["real_database"] == "healthy"
    assert data["honeypot_database"] == "healthy"