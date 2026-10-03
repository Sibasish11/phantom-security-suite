#!/usr/bin/env python3
"""Provision a dedicated local SOC tenant using authenticated public APIs.

Requires PhantomLayer DEMO_MODE=true. Never bypasses verification in production,
never reads production data, and never prints generated passwords or tokens.
"""
import json
from pathlib import Path
import secrets
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8000'


def read_env(path):
    if not path.exists():
        return {}
    return dict(line.split('=', 1) for line in path.read_text().splitlines()
                if '=' in line and not line.startswith('#'))


def write_env(path, values):
    # Runtime-only generated files are ignored by Git and owner-readable.
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    path.write_text(''.join(f'{key}={value}\n' for key, value in values.items()))


def main():
    from connect import publish_challenge, install
    token = None
    def call(path, payload=None, headers=None, method=None):
        h = {'Content-Type': 'application/json', **(headers or {})}
        if token:
            h['Authorization'] = f'Bearer {token}'
        try:
            with urlopen(Request(BASE + path, headers=h, method=method,
                data=json.dumps(payload).encode() if payload is not None else None), timeout=15) as response:
                return json.load(response)
        except HTTPError as exc:
            raise RuntimeError(f'Provisioning {path} returned HTTP {exc.code}; verify local DEMO_MODE and credentials') from None
    config = read_env(ROOT / '.env')
    if not config.get('AUTH_SECRET_KEY'):
        raise SystemExit('Run ./scripts/setup.sh before provisioning')
    login_file = ROOT / '.env.demo-login'
    credentials = read_env(login_file)
    if not credentials:
        suffix = secrets.token_hex(4)
        credentials = {'PHANTOMLAYER_EMAIL': f'defender-{suffix}@phantombank.example.com',
                       'PHANTOMLAYER_PASSWORD': secrets.token_urlsafe(24)}
        result = call('/auth/register', {
            'company_name': f'PhantomBank Demo {suffix}', 'full_name': 'PhantomBank Defender',
            'email': credentials['PHANTOMLAYER_EMAIL'], 'password': credentials['PHANTOMLAYER_PASSWORD'],
        })
        write_env(login_file, credentials)
    else:
        result = call('/auth/login', {'email': credentials['PHANTOMLAYER_EMAIL'],
                                     'password': credentials['PHANTOMLAYER_PASSWORD']})
    token = result['access_token']
    domains = call('/domains')
    domain = next((row for row in domains if row['domain'] == 'phantombank.example.test'), None)
    if domain is None:
        domain = call('/domains', {'domain': 'phantombank.example.test'})
    if not domain['verified']:
        domain = call(f"/domains/{domain['id']}/renew-challenge", {})
        publish_challenge(domain['verification_token'])
        call(f"/domains/{domain['id']}/demo-verify", {})
    protections = call('/protections')
    protection = next((row for row in protections if row['domain_id'] == domain['id']), None)
    if protection is None:
        call('/protections', {'domain_id': domain['id'], 'layer': 'api'})
    elif not protection['enabled'] or protection['layer'] != 'api':
        call('/protections/' + protection['id'], {'layer': 'api', 'enabled': True}, method='PATCH')
    agents = call('/agents')
    agent = next((row for row in agents if row['agent_id'] == config.get('AGENT_ID') and row['domain_id'] == domain['id']), None)
    if agent is None:
        registration = call('/agents/register', {'name': f'PhantomBank proxy {secrets.token_hex(3)}',
                            'domain_id': domain['id'], 'version': '0.2.0',
                            'capabilities': ['api-protection', 'honeypot-routing', 'telemetry']})
        config['AGENT_ID'] = registration['agent_id']
        config['AGENT_TOKEN'] = registration['registration_token']
    install({'agent_id': config['AGENT_ID'], 'agent_token': config['AGENT_TOKEN'],
             'organization_id': result['user']['organization_id'], 'domain_id': domain['id'],
             'domain': domain['domain']})
    print('Dedicated local PhantomBank SOC tenant and agent provisioned.')
    print('Defender credentials: PhantomBank/.env.demo-login (owner-only; not committed)')
    print('bank-api has loaded the customer integration. No datasets were reset.')


if __name__ == '__main__':
    main()
