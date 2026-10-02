#!/usr/bin/env python3
"""Loopback-only end-to-end proof using real PostgreSQL audit evidence.

The initial valid synthetic login reads the real authentication record. The
proof starts AFTER that login and shows that no subsequent attacker operation
changes real bank rows OR its gateway audit ledger. Nothing is deleted/reset.
"""
import hashlib
import http.cookiejar
import json
from pathlib import Path
import subprocess
from urllib.request import Request, HTTPCookieProcessor, build_opener

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8001'
jar = http.cookiejar.CookieJar()
client = build_opener(HTTPCookieProcessor(jar))


def call(path, data=None):
    with client.open(Request(BASE + path, data=json.dumps(data).encode() if data is not None else None,
                            headers={'Origin': 'http://localhost:3001', 'Content-Type': 'application/json'}), timeout=15) as response:
        assert response.status == 200
        return json.load(response)


def real_fingerprint():
    program = '''
import hashlib, json
from app.db import Database
from app.config import settings
r = Database(settings.real_database_url, 'real')
data = {table: r.query('SELECT * FROM ' + table + ' ORDER BY id')
        for table in ('bank_customers','accounts','transactions','transfers','beneficiaries','cards','gateway_audit')}
print(hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest())
'''
    return subprocess.check_output(['docker', 'compose', 'exec', '-T', 'bank-api', 'python', '-c', program], cwd=ROOT, text=True).strip()


def main():
    call('/api/auth/login', {'email': 'maya.bennett@northstar.test', 'password': 'DemoMaya!2025'})
    # The benign account flow works before the session is classified.
    assert len(call('/api/accounts')['accounts']) > 0
    before = real_fingerprint()
    for path in ('list-tables', 'enumerate-api', 'customers', 'accounts', 'transactions',
                 'probe-admin', 'customers', 'credential-probe'):
        result = call('/api/security/' + path)['result']
        if path == 'customers':
            assert any(row['full_name'] == 'John Carter' for row in result['records'])
            assert all(row['full_name'] != 'Maya Bennett' for row in result['records'])
        print('PASS', path)
    # Low-risk-looking operations cannot escape the pinned deception session.
    assert call('/api/profile')['profile']['full_name'] == 'John Carter'
    assert real_fingerprint() == before, 'Real bank data or audit changed after diversion!'
    print('PASS: real PostgreSQL data AND access audit unchanged after reconnaissance')
    print('PASS: attacker sees John Carter; benign-looking follow-up remains in deception')


if __name__ == '__main__':
    main()
