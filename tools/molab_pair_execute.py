"""Windows OpenSSL transport for a paired marimo scratchpad.

Read MARIMO_TOKEN from the process environment; never print it. This is a
transport helper, not a remote execution agent or detached-job launcher.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('code_file', type=Path)
    args = parser.parse_args()
    token = os.environ.get('MARIMO_TOKEN')
    if not token:
        raise SystemExit('MARIMO_TOKEN missing')
    if not re.fullmatch(r'[0-9a-f]{64}', token):
        raise SystemExit('MARIMO_TOKEN does not match the expected paired token format')
    base = args.url.rstrip('/')
    if not base.startswith('https://sb-') or not base.endswith('.sb.molab.run'):
        raise SystemExit('Unexpected paired Molab host')
    headers = {'Authorization': f'Bearer {token}'}
    session = requests.Session()
    listing = session.get(base + '/api/sessions', headers=headers, timeout=20)
    listing.raise_for_status()
    sessions = listing.json()
    if len(sessions) != 1:
        raise SystemExit(f'Expected one Molab session, found {len(sessions)}')
    session_id = next(iter(sessions))
    code = args.code_file.read_text(encoding='utf-8')
    response = session.post(base + '/api/kernel/execute',
                            headers={**headers, 'Marimo-Session-Id': session_id},
                            json={'code': code}, stream=True, timeout=(20, None))
    response.raise_for_status()
    kind = None
    done = False
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith('event:'):
            kind = line[6:].strip()
        elif line.startswith('data:'):
            payload = json.loads(line[5:].strip())
            if kind in ('stdout', 'stderr'):
                destination = sys.stdout if kind == 'stdout' else sys.stderr
                print(payload.get('data', ''), end='', file=destination, flush=True)
            elif kind == 'done':
                done = True
                if not payload.get('success', False):
                    raise SystemExit('Molab code execution failed')
                if payload.get('output', {}).get('data'):
                    print(payload['output']['data'], flush=True)
                break
    if not done:
        raise SystemExit('Molab SSE ended without done')


if __name__ == '__main__':
    main()
