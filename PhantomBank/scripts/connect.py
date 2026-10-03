#!/usr/bin/env python3
"""Customer-host setup. Credentials go to owner-only .env, never command arguments/logs."""
import argparse
import getpass
import json
import re
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from uuid import UUID

from provision_demo import ROOT, read_env, write_env


def restart():
    subprocess.run(['docker', 'compose', 'up', '-d', '--wait', 'bank-api'], cwd=ROOT, check=True)


def publish_challenge(token):
    if not re.fullmatch(r'[a-f0-9]{32}', token):
        raise ValueError('Expected the 32-character TXT challenge from your domain page')
    config = read_env(ROOT / '.env')
    with urlopen('http://127.0.0.1:8001/api/integration-info', timeout=10) as response:
        local_info = json.load(response)
    if local_info.get('demo_mode') is not True:
        raise ValueError('Local challenge publishing requires DEMO_MODE=true')
    config['DOMAIN_VERIFICATION_TOKEN'] = token
    write_env(ROOT / '.env', config)
    restart()


def install(bundle):
    config = read_env(ROOT / '.env')
    agent_id = str(UUID(bundle['agent_id']))
    token = bundle['agent_token']
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', token):
        raise ValueError('Invalid agent credential format')
    # The local compose contract fixes this URL; downloaded files cannot redirect
    # secrets to an arbitrary server. A production adapter uses its operator URL.
    with urlopen(Request('http://127.0.0.1:8000/integrations/bank/identity', headers={
        'X-Agent-ID': agent_id, 'X-Agent-Token': token,
    }), timeout=10) as response:
        identity = json.load(response)
    for field in ('agent_id', 'organization_id', 'domain_id', 'domain'):
        if identity[field] != bundle[field]:
            raise ValueError('Integration bundle does not match the authenticated agent identity')
    if identity['domain'] != 'phantombank.example.test':
        raise ValueError('This local bank uses phantombank.example.test; onboard that reserved demo domain')
    config.update(AGENT_ID=agent_id, AGENT_TOKEN=token, PROTECTION_MODE='protected')
    write_env(ROOT / '.env', config)
    restart()
    print(f"Connected customer organization {identity['organization_id']} / domain {identity['domain']}")
    print('Wait for the real bank-api heartbeat on the PhantomLayer activation page.')


def standalone():
    """Explicit presenter deployment change, never an on-error fallback."""
    with urlopen('http://127.0.0.1:8001/api/integration-info', timeout=10) as response:
        info = json.load(response)
    if not info.get('demo_mode'):
        raise ValueError('Standalone demonstration requires DEMO_MODE')
    if info['mode'] == 'standalone':
        print('Already in local standalone mode.')
        return
    backup = ROOT / '.env.integration-backup'
    # Exclusive creation: never overwrite an existing operator recovery file.
    with backup.open('x') as stream:
        backup.chmod(0o600)
        stream.write((ROOT / '.env').read_text())
    config = read_env(ROOT / '.env')
    config.update(PROTECTION_MODE='standalone', AGENT_ID='', AGENT_TOKEN='')
    write_env(ROOT / '.env', config)
    restart()
    print('Local standalone bank ready. Original connection saved privately; restore with scripts/connect.py restore.')


def restore():
    backup = ROOT / '.env.integration-backup'
    if not backup.is_file():
        raise ValueError('No connection backup')
    write_env(ROOT / '.env', read_env(backup))
    restart()
    backup.unlink()
    print('Original customer connection restored; bank datasets were preserved.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('verify', help='Publish your local domain challenge (interactive)')
    commands.add_parser('standalone', help='Explicit local BEFORE deployment; privately backs up current connection')
    commands.add_parser('restore', help='Restore the connection saved by standalone')
    command = commands.add_parser('install', help='Install the one-time downloaded customer bundle')
    command.add_argument('bundle', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'verify':
            publish_challenge(getpass.getpass('Paste your PhantomLayer TXT challenge: ').strip())
            print('Challenge published. Click Use local demo verification in PhantomLayer.')
        elif args.command == 'standalone':
            standalone()
        elif args.command == 'restore':
            restore()
        else:
            args.bundle.chmod(0o600)
            install(json.loads(args.bundle.read_text()))
    except (KeyError, ValueError, HTTPError, URLError, FileExistsError):
        # Do not include request objects, bundles, or secrets in errors.
        raise SystemExit('Setup failed: check the challenge, authenticated bundle, enabled API protection and local services.') from None


if __name__ == '__main__':
    main()
