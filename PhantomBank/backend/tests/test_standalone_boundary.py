import pytest
from app.config import Settings, settings
from app.gateway import PhantomLayerDecisionClient, ProtectionUnavailable


def test_standalone_is_never_a_production_or_configured_agent_fallback():
    with pytest.raises(ValueError):
        Settings(protection_mode='standalone', demo_mode=False)
    with pytest.raises(ValueError):
        Settings(protection_mode='standalone', demo_mode=True, agent_id='installed')


def test_presenter_authority_required_for_baseline_real_path(client, monkeypatch):
    from app import main
    monkeypatch.setattr(settings, 'demo_mode', True)
    monkeypatch.setattr(settings, 'protection_mode', 'standalone')
    monkeypatch.setattr(settings, 'defender_evidence_token', 'local-presenter-test')
    monkeypatch.setattr(main.gateway, 'decision_client', PhantomLayerDecisionClient())
    monkeypatch.setattr(main, '_client_ip', lambda request: '127.0.0.1')
    assert client.post('/api/auth/login', headers={'Origin': 'http://testserver'}, json={
        'email': 'maya.bennett@northstar.test', 'password': 'DemoMaya!2025'}).status_code == 200
    assert client.get('/api/security/customers').status_code == 404
    response = client.get('/api/security/customers', headers={'X-Demo-Runner': 'local-presenter-test'})
    assert response.status_code == 200
    assert response.json()['result']['records'][0]['full_name'] == 'Maya Bennett'
    monkeypatch.setattr(settings, 'protection_mode', 'protected')
    # Missing/unavailable protection does not fall back to the standalone path.
    def unavailable():
        raise ProtectionUnavailable()
    monkeypatch.setattr(main.gateway.decision_client, '_ensure_configured', unavailable)
    assert client.get('/api/security/customers', headers={'X-Demo-Runner': 'local-presenter-test'}).status_code == 503
