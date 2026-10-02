import pytest
from fastapi.testclient import TestClient
from uuid import UUID

from app.security_logging.service import (
    SecurityEventLogger,
    event_store,
    security_event_logger,
)
from app.security_logging.schemas import (
    EventSource,
    EventType,
    SecurityEvent,
)
from app.routing.service import automatic_routing_service
from app.routing.schemas import RoutingRequest
from app.main import app


@pytest.fixture
def client(authenticated_client):
    return authenticated_client


@pytest.fixture(autouse=True)
def clear_events(memory_event_store):
    event_store.clear()
    yield
    event_store.clear()


def test_event_creation():
    event = SecurityEvent(
        event_type=EventType.REQUEST_ANALYZED,
        source=EventSource.ROUTING,
        original_target="real",
        operation="health_check",
        risk_score=0,
        severity="LOW",
        confidence=0.0,
        confidence_level="LOW",
        suspicious=False,
        reasons=[],
    )
    assert event.event_type == EventType.REQUEST_ANALYZED
    assert event.source == EventSource.ROUTING
    assert isinstance(event.event_id, UUID)
    assert event.timestamp.tzinfo is not None  # timezone-aware


def test_unique_event_ids():
    event1 = SecurityEvent(
        event_type=EventType.REQUEST_ANALYZED,
        source=EventSource.ROUTING,
        original_target="real",
        operation="health_check",
    )
    event2 = SecurityEvent(
        event_type=EventType.REQUEST_ANALYZED,
        source=EventSource.ROUTING,
        original_target="real",
        operation="health_check",
    )
    assert event1.event_id != event2.event_id


def test_event_store_insertion():
    event = SecurityEvent(
        event_type=EventType.REQUEST_ANALYZED,
        source=EventSource.ROUTING,
        original_target="real",
        operation="health_check",
    )
    event_store.add(event)
    assert event_store.count() == 1


def test_event_store_insertion_order():
    event1 = SecurityEvent(
        event_type=EventType.REQUEST_ANALYZED,
        source=EventSource.ROUTING,
        original_target="real",
        operation="health_check",
    )
    event2 = SecurityEvent(
        event_type=EventType.SUSPICIOUS_REQUEST,
        source=EventSource.DETECTION,
        original_target="real",
        operation="get_users",
    )
    event3 = SecurityEvent(
        event_type=EventType.ROUTING_DECISION,
        source=EventSource.ROUTING,
        original_target="real",
        operation="get_users",
    )
    event_store.add(event1)
    event_store.add(event2)
    event_store.add(event3)

    recent = event_store.get_recent(limit=10)
    # get_recent returns reversed (newest first)
    assert recent[0].event_type == EventType.ROUTING_DECISION
    assert recent[1].event_type == EventType.SUSPICIOUS_REQUEST
    assert recent[2].event_type == EventType.REQUEST_ANALYZED


def test_get_event_by_id():
    event = SecurityEvent(
        event_type=EventType.REQUEST_ANALYZED,
        source=EventSource.ROUTING,
        original_target="real",
        operation="health_check",
    )
    event_store.add(event)

    retrieved = event_store.get_by_id(event.event_id)
    assert retrieved is not None
    assert retrieved.event_id == event.event_id
    assert retrieved.operation == "health_check"


def test_get_nonexistent_event():
    from uuid import uuid4
    retrieved = event_store.get_by_id(uuid4())
    assert retrieved is None


def test_recent_events_limit():
    for i in range(5):
        event = SecurityEvent(
            event_type=EventType.REQUEST_ANALYZED,
            source=EventSource.ROUTING,
            original_target="real",
            operation=f"op_{i}",
        )
        event_store.add(event)

    recent = event_store.get_recent(limit=3)
    assert len(recent) == 3
    assert recent[0].operation == "op_4"
    assert recent[1].operation == "op_3"
    assert recent[2].operation == "op_2"


def test_clear_events():
    for i in range(3):
        event = SecurityEvent(
            event_type=EventType.REQUEST_ANALYZED,
            source=EventSource.ROUTING,
            original_target="real",
            operation=f"op_{i}",
        )
        event_store.add(event)

    assert event_store.count() == 3
    event_store.clear()
    assert event_store.count() == 0


def test_get_by_type():
    event1 = SecurityEvent(
        event_type=EventType.REQUEST_ANALYZED,
        source=EventSource.ROUTING,
        original_target="real",
        operation="health_check",
    )
    event2 = SecurityEvent(
        event_type=EventType.SUSPICIOUS_REQUEST,
        source=EventSource.DETECTION,
        original_target="real",
        operation="get_users",
    )
    event3 = SecurityEvent(
        event_type=EventType.SUSPICIOUS_REQUEST,
        source=EventSource.DETECTION,
        original_target="real",
        operation="get_customers",
    )
    event_store.add(event1)
    event_store.add(event2)
    event_store.add(event3)

    suspicious = event_store.get_by_type(EventType.SUSPICIOUS_REQUEST)
    assert len(suspicious) == 2
    assert all(e.event_type == EventType.SUSPICIOUS_REQUEST for e in suspicious)


def test_get_by_source():
    event1 = SecurityEvent(
        event_type=EventType.REQUEST_ANALYZED,
        source=EventSource.ROUTING,
        original_target="real",
        operation="health_check",
    )
    event2 = SecurityEvent(
        event_type=EventType.SUSPICIOUS_REQUEST,
        source=EventSource.DETECTION,
        original_target="real",
        operation="get_users",
    )
    event_store.add(event1)
    event_store.add(event2)

    routing_events = event_store.get_by_source(EventSource.ROUTING)
    detection_events = event_store.get_by_source(EventSource.DETECTION)
    assert len(routing_events) == 1
    assert len(detection_events) == 1


def test_logging_health_endpoint(client):
    response = client.get("/logging/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "PhantomLayer Security Event Logging"
    assert data["status"] == "healthy"
    assert "events_stored" in data
    assert "event_types_supported" in data


def test_events_endpoint_empty(client):
    response = client.get("/logging/events")
    assert response.status_code == 200
    data = response.json()
    assert data["events"] == []
    assert data["total"] == 0
    assert data["limit"] == 100


def test_events_endpoint_with_limit(client):
    # Add some events directly
    logger = SecurityEventLogger(event_store)
    for i in range(5):
        logger.log_request_analyzed(
            original_target="real",
            operation=f"op_{i}",
            risk_score=0,
            severity="LOW",
            confidence=0.0,
            confidence_level="LOW",
            suspicious=False,
            triggered_rules=[],
            reasons=[],
            routing_decision="pending",
            routing_reason="test",
        )

    response = client.get("/logging/events?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 3
    assert data["total"] == 5
    assert data["limit"] == 3


def test_event_by_id_endpoint(client):
    logger = SecurityEventLogger(event_store)
    event = logger.log_request_analyzed(
        original_target="real",
        operation="health_check",
        risk_score=0,
        severity="LOW",
        confidence=0.0,
        confidence_level="LOW",
        suspicious=False,
        triggered_rules=[],
        reasons=[],
        routing_decision="pending",
        routing_reason="test",
    )

    response = client.get(f"/logging/events/{event.event_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == str(event.event_id)
    assert data["operation"] == "health_check"


def test_event_by_invalid_id(client):
    response = client.get("/logging/events/invalid-uuid")
    assert response.status_code == 400


def test_event_by_nonexistent_id(client):
    from uuid import uuid4
    response = client.get(f"/logging/events/{uuid4()}")
    assert response.status_code == 404


def test_clear_events_endpoint(client):
    logger = SecurityEventLogger(event_store)
    logger.log_request_analyzed(
        original_target="real",
        operation="health_check",
        risk_score=0,
        severity="LOW",
        confidence=0.0,
        confidence_level="LOW",
        suspicious=False,
        triggered_rules=[],
        reasons=[],
        routing_decision="pending",
        routing_reason="test",
    )
    assert event_store.count() == 1

    response = client.post("/logging/events/clear")
    # Global deletion of security evidence is deliberately no longer an API.
    assert response.status_code in (404, 405)
    assert event_store.count() == 1


@pytest.mark.asyncio
async def test_automatic_logging_normal_request():
    event_store.clear()
    request = RoutingRequest(target="real", operation="health_check")
    await automatic_routing_service.route(request)

    events = event_store.get_all()
    assert len(events) >= 2

    # Check request_analyzed event
    analyzed = [e for e in events if e.event_type == EventType.REQUEST_ANALYZED]
    assert len(analyzed) == 1
    assert analyzed[0].original_target == "real"
    assert analyzed[0].operation == "health_check"
    assert analyzed[0].risk_score == 0
    assert analyzed[0].suspicious is False
    assert analyzed[0].routing_decision == "pending"

    # Check routing_decision event
    routing = [e for e in events if e.event_type == EventType.ROUTING_DECISION]
    assert len(routing) == 1
    assert routing[0].routing_decision == "original_target_preserved"
    assert routing[0].original_target == "real"
    assert routing[0].final_target == "real"

    # Verify no sensitive data in events
    for event in events:
        assert "data" not in event.metadata
        assert "password" not in str(event.metadata).lower()
        assert "email" not in str(event.metadata).lower()


@pytest.mark.asyncio
async def test_automatic_logging_suspicious_request():
    event_store.clear()
    request = RoutingRequest(target="real", operation="get_users")
    await automatic_routing_service.route(request)

    events = event_store.get_all()

    # Check request_analyzed
    analyzed = [e for e in events if e.event_type == EventType.REQUEST_ANALYZED]
    assert len(analyzed) == 1
    assert analyzed[0].suspicious is True

    # Check suspicious_request
    suspicious = [e for e in events if e.event_type == EventType.SUSPICIOUS_REQUEST]
    assert len(suspicious) == 1
    assert suspicious[0].original_target == "real"
    assert suspicious[0].final_target == "honeypot"
    assert suspicious[0].suspicious is True
    assert len(suspicious[0].triggered_rules) > 0

    # Check routing_decision
    routing = [e for e in events if e.event_type == EventType.ROUTING_DECISION]
    assert len(routing) == 1
    assert routing[0].routing_decision == "routed_to_honeypot"

    # Check honeypot_interaction
    honeypot = [e for e in events if e.event_type == EventType.HONEYPOT_INTERACTION]
    assert len(honeypot) == 1
    assert honeypot[0].final_target == "honeypot"
    assert honeypot[0].gateway_success is True
    assert "result_count" in honeypot[0].metadata
    assert honeypot[0].metadata["result_count"] == 5


@pytest.mark.asyncio
async def test_automatic_logging_honeypot_target():
    event_store.clear()
    request = RoutingRequest(target="honeypot", operation="health_check")
    await automatic_routing_service.route(request)

    events = event_store.get_all()

    suspicious = [e for e in events if e.event_type == EventType.SUSPICIOUS_REQUEST]
    assert len(suspicious) == 1
    assert suspicious[0].original_target == "honeypot"
    assert suspicious[0].final_target == "honeypot"


@pytest.mark.asyncio
async def test_automatic_logging_reconnaissance():
    event_store.clear()
    request = RoutingRequest(target="real", operation="list_tables")
    await automatic_routing_service.route(request)

    events = event_store.get_all()

    suspicious = [e for e in events if e.event_type == EventType.SUSPICIOUS_REQUEST]
    assert len(suspicious) == 1
    assert suspicious[0].final_target == "honeypot"
    rule_names = [r["rule"] for r in suspicious[0].triggered_rules]
    assert "RULE_ENUMERATION" in rule_names
    assert "RULE_RECONNAISSANCE" in rule_names


@pytest.mark.asyncio
async def test_automatic_logging_gateway_failure():
    event_store.clear()
    request = RoutingRequest(target="real", operation="drop_table")
    await automatic_routing_service.route(request)

    events = event_store.get_all()

    failure = [e for e in events if e.event_type == EventType.GATEWAY_FAILURE]
    assert len(failure) == 1
    assert failure[0].gateway_success is False
    assert failure[0].metadata["error"] == "Unsupported operation: drop_table"


@pytest.mark.asyncio
async def test_automatic_logging_sensitive_data_not_logged():
    event_store.clear()
    request = RoutingRequest(target="real", operation="get_users")
    result = await automatic_routing_service.route(request)

    # Verify the routing response has the data
    assert result.gateway_result is not None
    assert len(result.gateway_result) == 5

    # Verify events don't contain the actual user records
    events = event_store.get_all()
    for event in events:
        metadata_str = str(event.metadata)
        # Should not contain actual user emails or names
        assert "admin@phantomlayer.demo" not in metadata_str
        assert "sysadmin@deception.local" not in metadata_str
        assert "john.manager" not in metadata_str
        # Should only contain result_count
        if event.event_type == EventType.HONEYPOT_INTERACTION:
            assert "result_count" in event.metadata


def test_logging_endpoint_after_routing(client):
    # Make a routing request
    response = client.post("/routing/route", json={
        "target": "real",
        "operation": "health_check",
    })
    assert response.status_code == 200

    # Check events via logging endpoint
    response = client.get("/logging/events")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2

    # Check event structure
    for event in data["events"]:
        assert "event_id" in event
        assert "timestamp" in event
        assert "event_type" in event
        assert "source" in event


def test_logging_endpoint_sensitive_data_not_exposed(client):
    response = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_users",
    })
    assert response.status_code == 200

    response = client.get("/logging/events")
    assert response.status_code == 200
    data = response.json()

    # Verify no actual user data in events
    for event in data["events"]:
        metadata_str = str(event.get("metadata", {}))
        assert "admin@phantomlayer.demo" not in metadata_str
        assert "sysadmin@deception.local" not in metadata_str