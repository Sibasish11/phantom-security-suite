#!/usr/bin/env python3
"""Same loopback-only, synthetic, read-only HTTP attack in both deployment modes."""
import argparse
import http.cookiejar
import json
import subprocess
from urllib.request import Request, build_opener, HTTPCookieProcessor

from provision_demo import ROOT, read_env

OPERATIONS = ('list-tables', 'enumerate-api', 'customers', 'accounts', 'transactions', 'probe-admin', 'customers', 'credential-probe')


def fingerprints():
    program = '''
import hashlib, json
from app.main import real_database, honeypot_database
result = {}
for database in (real_database, honeypot_database):
    tables = ('bank_customers','accounts','transactions','transfers','beneficiaries','cards')
    rows = {t: database.query('SELECT * FROM ' + t + ' ORDER BY id') for t in tables}
    result[database.name] = hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()
    result[database.name + '_audit'] = hashlib.sha256(json.dumps(database.query('SELECT * FROM gateway_audit ORDER BY id'), sort_keys=True, default=str).encode()).hexdigest()
print(json.dumps(result))
'''
    return json.loads(subprocess.check_output(['docker', 'compose', 'exec', '-T', 'bank-api', 'python', '-c', program], cwd=ROOT, text=True))


def run(phase):
    client = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    secret = read_env(ROOT / '.env')['DEFENDER_EVIDENCE_TOKEN']
    def call(path, body=None):
        with client.open(Request('http://127.0.0.1:8001' + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Origin': 'http://localhost:3001', 'Content-Type': 'application/json', 'X-Demo-Runner': secret}), timeout=15) as response:
            return json.load(response)
    info = call('/api/integration-info')
    assert info['demo_mode'], 'Local synthetic demonstration only'
    assert info['mode'] == ('standalone' if phase == 'before' else 'protected'), 'Use the matching deployment phase; no automatic bypass is performed'
    call('/api/auth/login', {'email': 'maya.bennett@northstar.test', 'password': 'DemoMaya!2025'})
    assert call('/api/accounts')['accounts']
    before = fingerprints()
    steps = []
    for operation in OPERATIONS:
        response = call('/api/security/' + operation)['result']
        evidence = call('/internal/defender-evidence?limit=1')['evidence'][-1]
        assert evidence['destination'] == ('real' if phase == 'before' else 'honeypot')
        if operation == 'customers':
            assert response['records'][0]['full_name'] == ('Maya Bennett' if phase == 'before' else 'John Carter')
        steps.append({'request': operation, 'response': response, **evidence})
    after = fingerprints()
    assert before['real'] == after['real'], 'Real business dataset changed'
    assert before['honeypot'] == after['honeypot'], 'Read-only run changed deception business dataset'
    if phase == 'after':
        assert before['real_audit'] == after['real_audit'], 'Diverted attack accessed instrumented real path'
    else:
        assert before['real_audit'] != after['real_audit'], 'Baseline should show instrumented real path access'
    return {'phase': phase, 'steps': steps, 'fingerprints_before': before, 'fingerprints_after': after,
            'proof': 'Bounded local allowlisted operations only; business data unchanged. Audit rows intentionally retained.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['before', 'after'])
    print(json.dumps(run(parser.parse_args().phase), indent=2))
