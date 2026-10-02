"""

Phase 11 — AI Incident Analysis: Test Suite



Covers:

 1.  Successful mock analysis (end-to-end via service)

 2.  Sanitized payload whitelist enforcement

 3.  Malicious/unauthorized fields excluded from payload

 4.  Missing session → 404 (service + API)

 5.  Empty session (0 interactions)

 6.  Malformed AI response (client raises IncidentAnalysisMalformedResponseError)

 7.  AI timeout (client raises IncidentAnalysisTimeoutError)

 8.  AI generic failure (client raises IncidentAnalysisError)

 9.  Incident report persistence (store)

10.  Repeated analysis – returns cached report

11.  Repeated analysis with force_reanalysis=True – re-runs

12.  Session/event correlation in sanitized payload

13.  POST /api/v1/incidents/{session_id}/analyze – HTTP 200

14.  POST /api/v1/incidents/{session_id}/analyze – HTTP 404 (unknown session)

15.  GET  /api/v1/incidents/{session_id} – HTTP 200

16.  GET  /api/v1/incidents/{session_id} – HTTP 404 (no report yet)

17.  GET  /api/v1/incidents – list all

18.  AI output never influences routing (regression check)

19.  Production-data exclusion from payload

20.  Multi-step session produces correct stage progression

"""



import asyncio

from unittest.mock import AsyncMock, patch



import pytest

from fastapi.testclient import TestClient



from app.honeypot.service import honeypot_session_manager

from app.incident_analysis.client import (

    BaseIncidentAnalysisClient,

    IncidentAnalysisError,

    IncidentAnalysisMalformedResponseError,

    IncidentAnalysisTimeoutError,

    MockAnalysisClient,

)

from app.incident_analysis.schemas import (

    AnalysisStatus,

    IncidentAnalysisRequest,

    IncidentAnalysisResponse,

    IncidentReport,

    SanitizedSessionPayload,

    SanitizedTimelineStep,

)

from app.incident_analysis.service import (

    IncidentReportStore,

    IncidentService,

    incident_report_store,

    incident_service,

)

from app.main import app

from app.routing.schemas import RoutingRequest

from app.routing.service import automatic_routing_service

from app.security_logging.service import event_store





# ---------------------------------------------------------------------------

# Fixtures

# ---------------------------------------------------------------------------





@pytest.fixture

def client(authenticated_client):

    return authenticated_client





@pytest.fixture(autouse=True)

def reset_stores():

    """Isolate each test by clearing all in-memory stores."""

    honeypot_session_manager.clear()

    event_store.clear()

    incident_report_store.clear()

    yield

    honeypot_session_manager.clear()

    event_store.clear()

    incident_report_store.clear()





def _make_service_with_mock() -> IncidentService:

    """Return a fresh IncidentService backed by MockAnalysisClient."""

    return IncidentService(

        store=IncidentReportStore(),

        client=MockAnalysisClient(),

    )





async def _route(operation: str, session_id: str = None, parameters: dict = None):

    """Helper: send a routing request to create honeypot interactions."""

    req = RoutingRequest(

        target="real",

        operation=operation,

        parameters=parameters,

        session_id=session_id,

    )

    return await automatic_routing_service.route(req)





# ---------------------------------------------------------------------------

# 1. Successful mock analysis – end-to-end via service

# ---------------------------------------------------------------------------





@pytest.mark.asyncio

async def test_successful_mock_analysis():

    session_id = "sess_phase11_success"



    # Create some honeypot activity

    await _route("list_tables", session_id)

    await _route("get_customers", session_id)

    await _route("get_customer", session_id, {"id": 1})



    svc = _make_service_with_mock()

    report = await svc.analyze_session(session_id)



    assert report.status == AnalysisStatus.COMPLETED

    assert report.session_id == session_id

    assert report.analysis is not None

    assert report.analysis.session_id == session_id

    assert report.analysis.analysis_provider == "mock"

    assert len(report.analysis.attack_stage_progression) >= 1

    assert len(report.analysis.timeline) >= 3

    assert report.sanitized_payload is not None





# ---------------------------------------------------------------------------

# 2. Sanitized payload whitelist enforcement

# ---------------------------------------------------------------------------





@pytest.mark.asyncio

async def test_sanitized_payload_whitelist():

    session_id = "sess_whitelist_check"

    await _route("get_customers", session_id)



    session = honeypot_session_manager.get_session(session_id)

    assert session is not None



    correlated = event_store.get_by_session(session_id)

    payload = IncidentService._build_sanitized_payload(session, correlated)



    # Must be a SanitizedSessionPayload

    assert isinstance(payload, SanitizedSessionPayload)

    # session_id is fine – it's a synthetic identifier, not a secret

    assert payload.session_id == session_id

    # Operations are included (enum-based names)

    assert "get_customers" in payload.unique_operations

    # Timeline steps exist

    assert len(payload.timeline) >= 1

    # Timeline steps only have the whitelisted fields

    step = payload.timeline[0]

    assert isinstance(step, SanitizedTimelineStep)

    assert hasattr(step, "operation")

    assert hasattr(step, "risk_score")

    assert hasattr(step, "attack_stage")

    assert hasattr(step, "entities_exposed_counts")

    assert hasattr(step, "success")

    # Counts only – never actual entity values

    assert isinstance(step.entities_exposed_counts, dict)





# ---------------------------------------------------------------------------

# 3. Unauthorized/sensitive fields EXCLUDED from payload

# ---------------------------------------------------------------------------





@pytest.mark.asyncio

async def test_unauthorized_fields_excluded():

    """

    Verify that client_ip, user_agent, raw gateway results, passwords,

    connection strings, and HTTP headers are NOT present in the sanitized

    payload.

    """

    session_id = "sess_exclusion_check"

    await _route("get_customers", session_id)



    session = honeypot_session_manager.get_session(session_id)

    correlated = event_store.get_by_session(session_id)

    payload = IncidentService._build_sanitized_payload(session, correlated)



    payload_dict = payload.model_dump()



    # These must NEVER appear in the sanitized payload

    forbidden_keys = {

        "client_ip", "user_agent", "password", "secret", "token",

        "api_key", "connection_string", "database_url", "gateway_result",

        "raw_request", "headers", "cookie",

    }



    def _check_no_forbidden(obj, path=""):

        if isinstance(obj, dict):

            for k, v in obj.items():

                assert k.lower() not in forbidden_keys, (

                    f"Forbidden key '{k}' found in sanitized payload at path '{path}.{k}'"

                )

                _check_no_forbidden(v, f"{path}.{k}")

        elif isinstance(obj, list):

            for i, item in enumerate(obj):

                _check_no_forbidden(item, f"{path}[{i}]")



    _check_no_forbidden(payload_dict)



    # Confirm actual entity values (emails, names) are NOT in the payload string

    payload_str = str(payload_dict)

    assert "james.anderson@corp.example" not in payload_str

    assert "James" not in payload_str  # first name should not appear





# ---------------------------------------------------------------------------

# 4. Missing session → ValueError from service, 404 from API

# ---------------------------------------------------------------------------





@pytest.mark.asyncio

async def test_missing_session_raises_value_error():

    svc = _make_service_with_mock()

    with pytest.raises(ValueError, match="not found"):

        await svc.analyze_session("sess_does_not_exist")





def test_missing_session_returns_404(client):

    resp = client.post("/api/v1/incidents/sess_ghost/analyze")

    assert resp.status_code == 404

    assert "not found" in resp.json()["detail"].lower()





# ---------------------------------------------------------------------------

# 5. Empty session (0 interactions)

# ---------------------------------------------------------------------------





@pytest.mark.asyncio

async def test_empty_session_analysis():

    """A session with no interactions should still produce a valid (minimal) report."""

    # Create a session directly without routing

    session = honeypot_session_manager.get_or_create_session(

        session_id="sess_empty",

        client_ip="10.0.0.1",

    )

    assert session.interaction_count == 0



    svc = _make_service_with_mock()

    report = await svc.analyze_session("sess_empty")



    assert report.status == AnalysisStatus.COMPLETED

    assert report.analysis is not None

    # Empty session: payload has 0 interactions and empty timeline

    assert report.sanitized_payload is not None

    assert report.sanitized_payload.total_interactions == 0

    assert report.sanitized_payload.timeline == []





# ---------------------------------------------------------------------------

# 6. Malformed AI response → FAILED report

# ---------------------------------------------------------------------------





class MalformedClient(BaseIncidentAnalysisClient):

    async def analyze(self, payload: SanitizedSessionPayload) -> IncidentAnalysisResponse:

        raise IncidentAnalysisMalformedResponseError("AI returned invalid JSON")





@pytest.mark.asyncio

async def test_malformed_ai_response():

    session_id = "sess_malformed"

    await _route("list_tables", session_id)



    svc = IncidentService(store=IncidentReportStore(), client=MalformedClient())

    report = await svc.analyze_session(session_id)



    assert report.status == AnalysisStatus.FAILED

    assert report.error == "Analysis provider returned an invalid response"





# ---------------------------------------------------------------------------

# 7. AI timeout → FAILED report

# ---------------------------------------------------------------------------





class TimeoutClient(BaseIncidentAnalysisClient):

    async def analyze(self, payload: SanitizedSessionPayload) -> IncidentAnalysisResponse:

        raise IncidentAnalysisTimeoutError("Provider timed out after 30s")





@pytest.mark.asyncio

async def test_ai_timeout():

    session_id = "sess_timeout"

    await _route("list_tables", session_id)



    svc = IncidentService(store=IncidentReportStore(), client=TimeoutClient())

    report = await svc.analyze_session(session_id)



    assert report.status == AnalysisStatus.FAILED

    assert "timed out" in report.error.lower()





# ---------------------------------------------------------------------------

# 8. Generic AI failure → FAILED report, HTTP 503 from API

# ---------------------------------------------------------------------------





class FailingClient(BaseIncidentAnalysisClient):

    async def analyze(self, payload: SanitizedSessionPayload) -> IncidentAnalysisResponse:

        raise IncidentAnalysisError("Rate limit exceeded")





@pytest.mark.asyncio

async def test_generic_ai_failure():

    session_id = "sess_ai_fail"

    await _route("list_tables", session_id)



    svc = IncidentService(store=IncidentReportStore(), client=FailingClient())

    report = await svc.analyze_session(session_id)



    assert report.status == AnalysisStatus.FAILED

    assert report.error == "Analysis provider unavailable"





def test_ai_failure_returns_503(client):

    """Patch the singleton incident_service to inject a failing client, then call the API."""

    session_id = "sess_503_test"



    # Create a real honeypot session so 404 isn't triggered

    honeypot_session_manager.get_or_create_session(session_id=session_id)



    # Patch the module-level incident_service with a failing one

    failing_svc = IncidentService(store=IncidentReportStore(), client=FailingClient())

    with patch("app.incident_analysis.router.incident_service", failing_svc):

        resp = client.post(f"/api/v1/incidents/{session_id}/analyze")



    assert resp.status_code == 503

    assert "AI analysis failed" in resp.json()["detail"]





# ---------------------------------------------------------------------------

# 9. Incident report persistence

# ---------------------------------------------------------------------------





@pytest.mark.asyncio

async def test_incident_report_persisted():

    session_id = "sess_persist_check"

    await _route("get_customers", session_id)



    svc = _make_service_with_mock()

    report = await svc.analyze_session(session_id)



    # Should be retrievable from the service's store

    retrieved = svc.get_report(session_id)

    assert retrieved is not None

    assert retrieved.report_id == report.report_id

    assert retrieved.status == AnalysisStatus.COMPLETED





# ---------------------------------------------------------------------------

# 10. Repeated analysis – returns cached report (no re-run)

# ---------------------------------------------------------------------------





@pytest.mark.asyncio

async def test_repeated_analysis_returns_cache():

    session_id = "sess_cache_test"

    await _route("list_tables", session_id)



    svc = _make_service_with_mock()

    report1 = await svc.analyze_session(session_id)

    report2 = await svc.analyze_session(session_id)  # should hit cache



    assert report1.report_id == report2.report_id

    assert svc._store.count() == 1  # only one report stored





# ---------------------------------------------------------------------------

# 11. Repeated analysis with force_reanalysis=True – re-runs

# ---------------------------------------------------------------------------





@pytest.mark.asyncio

async def test_force_reanalysis():

    session_id = "sess_force_reanalysis"

    await _route("list_tables", session_id)



    svc = _make_service_with_mock()

    report1 = await svc.analyze_session(session_id)

    report2 = await svc.analyze_session(session_id, force_reanalysis=True)



    # Both should succeed; report IDs differ because a new IncidentReport is created

    assert report1.status == AnalysisStatus.COMPLETED

    assert report2.status == AnalysisStatus.COMPLETED

    # The store should still have exactly one record (latest overwrites)

    assert svc._store.count() == 1





# ---------------------------------------------------------------------------

# 12. Session/event correlation in sanitized payload

# ---------------------------------------------------------------------------





@pytest.mark.asyncio

async def test_session_event_correlation():

    session_id = "sess_correlation_test"

    # Both get_customers and get_users route to honeypot (sensitive access)

    await _route("get_customers", session_id)

    await _route("get_users", session_id)



    session = honeypot_session_manager.get_session(session_id)

    correlated = event_store.get_by_session(session_id)



    assert len(correlated) >= 2, "Should have security events from routing"



    payload = IncidentService._build_sanitized_payload(session, correlated)

    assert payload.correlated_event_count == len(correlated)

    assert payload.total_interactions == 2

    assert "get_customers" in payload.unique_operations

    assert "get_users" in payload.unique_operations





# ---------------------------------------------------------------------------

# 13. POST /api/v1/incidents/{session_id}/analyze – HTTP 200

# ---------------------------------------------------------------------------





def test_api_analyze_returns_200(client):

    session_id = "sess_api_analyze_200"



    # Use HTTP routing to create the session

    r = client.post("/routing/route", json={

        "target": "real",

        "operation": "get_customers",

        "session_id": session_id,

    })

    assert r.status_code == 200



    # Trigger AI analysis via API

    resp = client.post(f"/api/v1/incidents/{session_id}/analyze")

    assert resp.status_code == 200

    data = resp.json()



    assert data["session_id"] == session_id

    assert data["status"] == "completed"

    assert data["analysis"] is not None

    assert "incident_summary" in data["analysis"]

    assert "attack_stage_progression" in data["analysis"]

    assert "defensive_recommendations" in data["analysis"]

    assert "likely_objective" in data["analysis"]

    assert "limitations" in data["analysis"]





# ---------------------------------------------------------------------------

# 14. POST /api/v1/incidents/{session_id}/analyze – HTTP 404

# ---------------------------------------------------------------------------





def test_api_analyze_returns_404(client):

    resp = client.post("/api/v1/incidents/sess_nonexistent_abc/analyze")

    assert resp.status_code == 404





# ---------------------------------------------------------------------------

# 15. GET /api/v1/incidents/{session_id} – HTTP 200

# ---------------------------------------------------------------------------





def test_api_get_report_returns_200(client):

    session_id = "sess_get_report_200"

    client.post("/routing/route", json={

        "target": "real",

        "operation": "list_tables",

        "session_id": session_id,

    })

    # Analyze first

    client.post(f"/api/v1/incidents/{session_id}/analyze")



    resp = client.get(f"/api/v1/incidents/{session_id}")

    assert resp.status_code == 200

    data = resp.json()

    assert data["session_id"] == session_id

    assert data["status"] == "completed"





# ---------------------------------------------------------------------------

# 16. GET /api/v1/incidents/{session_id} – HTTP 404 (no report yet)

# ---------------------------------------------------------------------------





def test_api_get_report_returns_pending_before_analysis(client):
    session_id = "sess_no_report_yet"

    # Routing now creates a pending incident automatically when
    # suspicious traffic is routed to the honeypot.
    route_response = client.post(
        "/routing/route",
        json={
            "target": "real",
            "operation": "list_tables",
            "session_id": session_id,
        },
    )

    assert route_response.status_code == 200

    resp = client.get(f"/api/v1/incidents/{session_id}")

    assert resp.status_code == 200

    data = resp.json()

    assert data["session_id"] == session_id
    assert data["status"] == "pending"



def test_api_list_reports(client):

    for i in range(3):

        sid = f"sess_list_test_{i}"

        client.post("/routing/route", json={

            "target": "real",

            "operation": "list_tables",

            "session_id": sid,

        })

        client.post(f"/api/v1/incidents/{sid}/analyze")



    resp = client.get("/api/v1/incidents")

    assert resp.status_code == 200

    data = resp.json()

    assert data["total"] >= 3

    assert len(data["reports"]) >= 3

    # Each summary should have required fields

    for r in data["reports"]:

        assert "report_id" in r

        assert "session_id" in r

        assert "status" in r





# ---------------------------------------------------------------------------

# 18. AI output NEVER influences routing (regression check)

# ---------------------------------------------------------------------------





@pytest.mark.asyncio

async def test_ai_output_does_not_influence_routing():

    """

    Core security invariant: routing decisions must remain identical

    regardless of whether an incident report has been generated.

    """

    session_id = "sess_routing_invariant"



    # Route once and record the decision

    req = RoutingRequest(target="real", operation="get_customers", session_id=session_id)

    resp_before = await automatic_routing_service.route(req)



    # Generate an AI incident report

    svc = _make_service_with_mock()

    report = await svc.analyze_session(session_id)

    assert report.status == AnalysisStatus.COMPLETED



    # Route again with the same session – decision must be identical

    req2 = RoutingRequest(target="real", operation="get_customers", session_id=session_id)

    resp_after = await automatic_routing_service.route(req2)



    assert resp_before.routing_decision == resp_after.routing_decision

    assert resp_before.final_target == resp_after.final_target





# ---------------------------------------------------------------------------

# 19. Production-data exclusion from sanitized payload

# ---------------------------------------------------------------------------





@pytest.mark.asyncio

async def test_production_data_excluded_from_payload():

    """

    Verify the sanitized payload does not contain real customer PII

    (even though the honeypot data is synthetic, the value itself must not leak).

    """

    session_id = "sess_pii_exclusion"

    await _route("get_customers", session_id)

    await _route("get_customer", session_id, {"id": 1})



    session = honeypot_session_manager.get_session(session_id)

    correlated = event_store.get_by_session(session_id)

    payload = IncidentService._build_sanitized_payload(session, correlated)



    payload_str = payload.model_dump_json()



    # Synthetic email values must NOT appear (entity values, only counts are permitted)

    assert "corp.example" not in payload_str

    assert "@" not in payload_str  # no email addresses

    # Order numbers must not appear

    assert "HPD-2024" not in payload_str

    # Passwords/secrets must not appear (negative check)

    assert "password" not in payload_str.lower()





# ---------------------------------------------------------------------------

# 20. Multi-step session produces correct stage progression

# ---------------------------------------------------------------------------





@pytest.mark.asyncio

async def test_multi_step_stage_progression():

    session_id = "sess_stage_progression"



    # list_tables → reconnaissance (routes to honeypot as reconnaissance)

    await _route("list_tables", session_id)

    # get_customers → enumeration (sensitive, routes to honeypot)

    await _route("get_customers", session_id)

    # get_customer → exploration (sensitive, routes to honeypot)

    await _route("get_customer", session_id, {"id": 1})

    # get_customers again → exfiltration (repeated sensitive access, previous_sensitive_count >= 2)

    await _route("get_customers", session_id)



    svc = _make_service_with_mock()

    report = await svc.analyze_session(session_id)



    assert report.status == AnalysisStatus.COMPLETED

    progression = report.analysis.attack_stage_progression

    assert "reconnaissance" in progression

    assert "enumeration" in progression

    assert "exploration" in progression

    assert "exfiltration" in progression



    # Final stage should be exfiltration

    assert report.sanitized_payload.final_attack_stage == "exfiltration"





# ---------------------------------------------------------------------------

# Regression: existing Phase 10 tests are invoked via pytest collection.

# This module does NOT import or re-run them explicitly; pytest discovers

# test_honeypot.py, test_routing.py, etc. automatically in the same run.

# ---------------------------------------------------------------------------
 