from dataclasses import replace
from uuid import UUID


def test_bank_reuses_original_uuid_not_phantomlayer_handle(client, monkeypatch):
    original_decide = client.stub.decide
    def namespaced_decide(**kwargs):
        decision = original_decide(**kwargs)
        return replace(decision, session_id='bank:agent-id:namespaced-session-hash',
                       request_session_id=kwargs['session_id'])
    monkeypatch.setattr(client.stub, 'decide', namespaced_decide)
    assert client.post('/api/auth/login', headers={'Origin':'http://localhost:3001'},
                       json={'email':'maya.bennett@northstar.test', 'password':'DemoMaya!2025'}).status_code == 200
    assert client.get('/api/accounts').status_code == 200
    assert client.get('/api/profile').status_code == 200
    requested_sessions = {session for session, operation in client.stub.decisions}
    assert len(requested_sessions) == 1
    UUID(requested_sessions.pop())
