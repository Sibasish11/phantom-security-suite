from __future__ import annotations

from app.gateway import PhantomLayerDecisionClient


def test_decision_adapter_sends_exact_server_only_contract(monkeypatch):
    import httpx
    from app.config import settings

    calls = []

    class Response:
        def __init__(self, body):
            self.body = body
        def raise_for_status(self):
            return None
        def json(self):
            return self.body

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["timeout"] == settings.phantomlayer_timeout_seconds
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def post(self, url, *, headers, json):
            calls.append((url, headers, json))
            if url.endswith("/decision"):
                return Response({
                    "decision_id": "00000000-0000-4000-8000-000000000020",
                    "session_id": "bank:agent-id:namespaced-session-hash",
                    "target": "real",
                    "risk_score": 4,
                    "attack_stage": "normal",
                    "triggered_rules": [],
                })
            return Response({"ok": True})

    monkeypatch.setattr(httpx, "Client", Client)
    client = PhantomLayerDecisionClient()
    decision = client.decide(
        session_id="00000000-0000-4000-8000-000000000021",
        operation="get_balance",
        client_ip="127.0.0.1",
    )
    assert decision.session_id == 'bank:agent-id:namespaced-session-hash'
    assert decision.request_session_id == '00000000-0000-4000-8000-000000000021'
    client.observe(decision=decision, success=True, exposed_entities={}, response_count=1)
    assert calls[0][0].endswith("/integrations/bank/decision")
    assert calls[0][1]["X-Agent-ID"] == "agent-unit-test"
    assert calls[0][1]["X-Agent-Token"] == "token-unit-test"
    assert calls[0][2] == {
        "session_id": "00000000-0000-4000-8000-000000000021",
        "operation": "get_balance",
        "client_ip": "127.0.0.1",
    }
    assert calls[1][0].endswith("/integrations/bank/observe")
    assert calls[1][2] == {
        "decision_id": "00000000-0000-4000-8000-000000000020",
        "success": True,
        "exposed_entities": {},
        "response_count": 1,
    }
