#!/usr/bin/env python3
"""Local restart proof. Restarts both APIs, not databases; bank users sign in again.

Run after provision_demo.py and safe_attack_simulation.py, with no concurrent
banking activity. Does not delete rows, databases, or volumes.
"""
import argparse
import json
import time
from urllib.error import URLError
from pathlib import Path
import subprocess
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PL = ROOT.parent / 'phantomlayer'
BASE = 'http://127.0.0.1:8000'


def read_env(path):
    return dict(line.split('=', 1) for line in path.read_text().splitlines()
                if '=' in line and not line.startswith('#'))


def bank_fingerprints():
    program = '''
import hashlib, json
from app.db import Database
from app.config import settings
out = {}
for target in ('real', 'honeypot'):
    database = Database(getattr(settings, target + '_database_url'), target)
    data = {table: database.query('SELECT * FROM ' + table + ' ORDER BY id')
            for table in ('bank_customers','accounts','transactions','transfers','beneficiaries','cards','gateway_audit')}
    out[target] = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()
print(json.dumps(out))
'''
    return json.loads(subprocess.check_output(
        ['docker', 'compose', 'exec', '-T', 'bank-api', 'python', '-c', program], cwd=ROOT, text=True))


def restart(directory, service, recreate=False):
    if recreate:
        subprocess.run(['docker', 'compose', 'up', '-d', '--wait', '--no-deps', '--force-recreate', service], cwd=directory, check=True)
    else:
        subprocess.run(['docker', 'compose', 'restart', service], cwd=directory, check=True)
        subprocess.run(['docker', 'compose', 'up', '-d', '--wait', service], cwd=directory, check=True)


def check_proxy(url, token=None):
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    for attempt in range(10):
        try:
            with urlopen(Request(url, headers=headers), timeout=3) as response:
                assert response.status == 200
                return
        except URLError:
            if attempt == 9:
                raise
            time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recreate', action='store_true', help='Recreate API containers to also check proxy DNS recovery')
    args = parser.parse_args()
    credentials = read_env(ROOT / '.env.demo-login')
    token = None
    def call(path, data=None):
        headers = {'Content-Type':'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        with urlopen(Request(BASE + path, headers=headers,
             data=json.dumps(data).encode() if data is not None else None), timeout=15) as response:
            return json.load(response)
    token = call('/auth/login', {'email':credentials['PHANTOMLAYER_EMAIL'],
                                'password':credentials['PHANTOMLAYER_PASSWORD']})['access_token']
    incidents = call('/incidents')['incidents']
    assert incidents, 'Run safe_attack_simulation.py to create a demo incident first'
    incident = incidents[0]
    session_id = incident['session_id']
    analyzed = call(f'/api/v1/incidents/{session_id}/analyze', {})
    assert analyzed['status'] == 'completed'
    assert analyzed['analysis']['analysis_provider'] == 'mock', 'This proof expects the labeled demo provider'
    timeline = call(f"/incidents/{incident['incident_id']}/timeline")
    events = call(f'/security/events?session_id={session_id}')
    assert timeline['timeline'] and events['events']
    restart(PL, 'backend', args.recreate)
    check_proxy('http://localhost:3000/organizations', token)
    reloaded = call(f'/api/v1/incidents/{session_id}')
    assert reloaded['report_id'] == analyzed['report_id']
    assert reloaded['analysis'] == analyzed['analysis']
    assert reloaded['status'] == 'completed'
    assert call(f"/incidents/{incident['incident_id']}/timeline") == timeline
    assert call(f'/security/events?session_id={session_id}') == events
    print('PASS: incident ID, completed mock analysis, timeline, and security events survive API restart')
    before = bank_fingerprints()
    restart(ROOT, 'bank-api', args.recreate)
    check_proxy('http://localhost:3001/health')
    assert bank_fingerprints() == before, 'Bank bootstrap changed persistent data or audit evidence'
    print('PASS: both bank datasets, transfers, and PostgreSQL audit rows survive bank API restart unchanged')
    print('PASS: both UI proxies reach the API after restart/recreation')
    print('Bank login sessions and the recent in-memory defender buffer reset on restart; sign in again.')


if __name__ == '__main__':
    main()
