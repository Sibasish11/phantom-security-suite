from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.config import settings
from app.database import get_sync_control_db_manager
from app.main import app
from app.models.control_plane import Agent, Organization, OrganizationStatus
from tests.dns_proof import verify_dns


def customer():
    client = TestClient(app)
    uid = uuid4().hex
    result = client.post('/auth/register', json={'company_name': f'Readiness {uid}',
        'full_name': 'QA Owner', 'email': f'{uid}@example.com', 'password': 'ReadinessPassword123!'}).json()
    client.headers['Authorization'] = f"Bearer {result['access_token']}"
    return client, result['user']['organization_id']


def test_local_proof_requires_published_challenge_and_demo_mode(monkeypatch):
    client, _ = customer()
    domain = client.post('/domains', json={'domain': 'phantombank.example.test'}).json()
    url = f"/domains/{domain['id']}/demo-verify"
    monkeypatch.setattr(settings, 'demo_mode', False)
    assert client.post(url).status_code == 403
    monkeypatch.setattr(settings, 'demo_mode', True)
    with patch('app.domains.service.httpx.Client') as factory:
        response = factory.return_value.__enter__.return_value.get.return_value
        response.json.return_value = {'domain': domain['domain'], 'token': 'wrong'}
        assert client.post(url).status_code == 422
        response.json.return_value['token'] = domain['verification_token']
        assert client.post(url).json()['verified'] is True
    other, _ = customer()
    assert other.post(url).status_code == 404


def test_readiness_rotation_staleness_pause_and_domain_binding():
    client, org = customer()
    domain = client.post('/domains', json={'domain': f'{uuid4().hex}.example.test'}).json()
    verify_dns(client, domain)
    protection = client.post('/protections', json={'domain_id': domain['id'], 'layer': 'api'}).json()
    path = '/protections/' + protection['id']
    assert protection['status'] == 'configuring'
    assert client.patch(path, json={'status': 'active'}).status_code == 422
    agent = client.post('/agents/register', json={'name': 'bank', 'domain_id': domain['id'], 'version': 'qa'}).json()
    assert client.get(path).json()['status'] == 'connecting'
    hp = '/agents/' + agent['agent_id'] + '/heartbeat'
    headers = {'X-Agent-Token': agent['registration_token']}
    body = {'status': 'healthy', 'real_db_reachable': True, 'honeypot_db_reachable': True}
    assert client.post(hp, json=body, headers=headers).status_code == 200
    assert client.get(path).json()['status'] != 'active'  # Health-only agent isn't the data path.
    body['integration_ready'] = True
    assert client.post(hp, json=body, headers=headers).status_code == 200
    assert client.get(path).json()['status'] == 'active'
    assert client.patch(path, json={'enabled': False}).json()['status'] == 'paused'
    assert client.patch(path, json={'enabled': True}).json()['status'] == 'active'
    body['honeypot_db_reachable'] = False
    assert client.post(hp, json=body, headers=headers).json()['status'] == 'degraded'
    assert client.get(path).json()['status'] == 'degraded'
    body['honeypot_db_reachable'] = True
    client.post(hp, json=body, headers=headers)
    with get_sync_control_db_manager().session() as db:
        db.get(Agent, UUID(agent['agent_id'])).last_heartbeat_at = datetime.now(timezone.utc) - timedelta(seconds=91)
        db.commit()  # Time travel in isolated QA database only.
    assert client.get('/agents/' + agent['agent_id']).json()['status'] == 'offline'
    assert client.get(path).json()['status'] == 'degraded'
    token = client.post('/agents/' + agent['agent_id'] + '/rotate-token').json()['registration_token']
    assert client.get(path).json()['status'] == 'connecting'
    assert client.post(hp, json=body, headers=headers).status_code == 401
    assert client.post(hp, json=body, headers={'X-Agent-Token': token}).status_code == 200
    with get_sync_control_db_manager().session() as db:
        db.get(Organization, UUID(org)).status = OrganizationStatus.SUSPENDED
        db.commit()
    assert TestClient(app).post(hp, json=body, headers={'X-Agent-Token': token}).status_code == 401
