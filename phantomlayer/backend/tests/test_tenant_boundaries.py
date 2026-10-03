"""Actual two-tenant API isolation, not mocked authorization."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.dns_proof import verify_dns


@pytest.fixture
def tenants():
    clients = []
    for _ in range(2):
        client = TestClient(app)
        uid = uuid4().hex
        registration = client.post('/auth/register', json={
            'company_name': f'Boundary {uid}', 'full_name': 'Test Defender',
            'email': f'{uid}@example.com', 'password': 'Boundary-Test-Password!'
        })
        assert registration.status_code == 201, registration.text
        client.headers['Authorization'] = f"Bearer {registration.json()['access_token']}"
        domain = client.post('/domains', json={'domain': f'{uid}.example.test'}).json()
        verify_dns(client, domain)
        client.headers['X-Domain-ID'] = domain['id']
        agent = client.post('/agents/register', json={
            'name': 'local-bank-proxy', 'domain_id': domain['id'], 'version': 'qa',
            'capabilities': ['bank-api'],
        })
        assert agent.status_code == 201, agent.text
        protection = client.post('/protections', json={'domain_id': domain['id'], 'layer': 'api'})
        assert protection.status_code == 201, protection.text
        clients.append((client, domain, agent.json(), protection.json()))
    return clients


def test_all_customer_resources_enforce_server_side_ownership(tenants):
    a, domain, agent, protection = tenants[0]
    b, _, b_agent, _ = tenants[1]
    agent_headers = {'X-Agent-ID': agent['agent_id'], 'X-Agent-Token': agent['registration_token']}
    sid = str(uuid4())
    decision = a.post('/integrations/bank/decision', headers=agent_headers,
                      json={'session_id': sid, 'operation': 'get_customers'})
    assert decision.status_code == 200, decision.text
    d = decision.json()
    observation = {'decision_id': d['decision_id'], 'success': True,
                   'exposed_entities': {'customers': 2}, 'response_count': 2}
    assert a.post('/integrations/bank/observe', headers=agent_headers, json=observation).status_code == 200
    incident = a.get('/incidents').json()['incidents'][0]
    event = a.get('/logging/events').json()['events'][0]
    paths = [f"/domains/{domain['id']}", f"/agents/{agent['agent_id']}",
             f"/protections/{protection['id']}", f"/incidents/{incident['incident_id']}",
             f"/incidents/{incident['incident_id']}/timeline", f"/honeypot/sessions/{d['session_id']}",
             f"/api/v1/incidents/{d['session_id']}", f"/logging/events/{event['event_id']}"]
    for path in paths:
        assert a.get(path).status_code == 200, path
        assert b.get(path).status_code == 404, path
    assert len(a.get('/organizations').json()) == 1
    assert len(b.get('/organizations').json()) == 1
    assert a.get('/organizations').json()[0]['id'] != b.get('/organizations').json()[0]['id']
    assert b.get('/incidents').json()['incidents'] == []
    assert b.get('/security/events').json()['events'] == []
    assert b.get('/security/events/recent').json()['events'] == []
    assert b.get('/honeypot/sessions').json()['sessions'] == []
    assert b.get('/security/stats').json()['requests_routed_to_honeypot'] == 0
    assert b.post(f"/api/v1/incidents/{d['session_id']}/analyze").status_code == 404
    assert b.post('/gateway/query', json={'target': 'real', 'operation': 'get_products',
                                         'session_id': d['session_id']}).status_code == 404
    assert b.patch(f"/protections/{protection['id']}", json={'enabled': False}).status_code == 404
    wrong_agent = {'X-Agent-ID': b_agent['agent_id'], 'X-Agent-Token': b_agent['registration_token']}
    assert b.post('/integrations/bank/observe', headers=wrong_agent, json=observation).status_code == 404
    # Body tenant selection is rejected, never used.
    assert a.post('/integrations/bank/decision', headers=agent_headers,
                  json={'session_id': sid, 'operation': 'get_accounts', 'organization_id': str(uuid4())}).status_code == 422
    # Replays cannot inflate interactions, and risk cannot reset on a benign op.
    assert a.post('/integrations/bank/observe', headers=agent_headers, json=observation).status_code == 200
    assert a.get(f"/honeypot/sessions/{d['session_id']}").json()['interaction_count'] == 1
    pinned = a.post('/integrations/bank/decision', headers=agent_headers,
                    json={'session_id': sid, 'operation': 'get_accounts'}).json()
    assert pinned['target'] == 'honeypot'
    assert pinned['risk_score'] >= d['risk_score']
    telemetry = {'event_id': str(uuid4()), 'agent_id': agent['agent_id'], 'session_id': sid,
                 'event_type': 'routing_decision', 'operation': 'get_customers',
                 'original_target': 'real', 'final_target': 'honeypot', 'risk_score': 70,
                 'severity': 'HIGH', 'suspicious': True, 'attack_stage': 'enumeration',
                 'metadata': {'password': 'must-never-be-stored'}}
    batch = {'events': [telemetry]}
    assert a.post('/agents/telemetry', headers=agent_headers, json=batch).json()['accepted'] == 1
    assert a.post('/agents/telemetry', headers=agent_headers, json=batch).json()['accepted'] == 0
    assert b.post('/agents/telemetry', headers=wrong_agent, json=batch).status_code == 401
    from app.database import get_sync_control_db_manager
    from app.models.control_plane import AttackSessionInteraction
    from sqlalchemy import select
    with get_sync_control_db_manager().session() as db:
        interaction = db.execute(select(AttackSessionInteraction).where(
            AttackSessionInteraction.event_id == telemetry['event_id'],
        )).scalar_one()
        assert 'must-never-be-stored' not in interaction.details
    assert a.patch(f"/protections/{protection['id']}", json={'enabled':False}).status_code == 200
    assert a.post('/integrations/bank/decision', headers=agent_headers,
                  json={'session_id':sid, 'operation':'get_accounts'}).status_code == 503


def test_unauthenticated_legacy_gateway_is_closed():
    client = TestClient(app)
    for path in ('/gateway/query', '/routing/route'):
        assert client.post(path, json={'target': 'real', 'operation': 'get_products'}).status_code == 401
