"""Unit fixture for a customer-published DNS TXT record, not an auth bypass."""
from types import SimpleNamespace
from unittest.mock import patch


def verify_dns(client, domain, headers=None):
    with patch('app.domains.service.dns.resolver.resolve', return_value=[
        SimpleNamespace(strings=[domain['verification_token'].encode()])
    ]):
        response = client.post(f"/domains/{domain['id']}/verify", headers=headers or {})
    assert response.status_code == 200, response.text
    return response.json()
