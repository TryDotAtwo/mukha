"""Windows HTTPS/SSE transport matching marimo-pair execute-code.sh."""
import json
import sys
from pathlib import Path
import requests
from contextlib import contextmanager


@contextmanager
def exclusive_execution(path):
    """Reject overlapping kernel requests; OS releases this lock on process exit.

    This protects this workspace's transport only. It does not establish remote
    job liveness after a transport failure; inspect Molab before submitting again.
    """
    with Path(path).open('a+b') as lock:
        if lock.tell() == 0:
            lock.write(b'\0')
            lock.flush()
        lock.seek(0)
        if sys.platform == 'win32':
            import msvcrt
            acquire = lambda: msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            release = lambda: msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            acquire = lambda: fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            release = lambda: fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        try:
            acquire()
        except OSError:
            raise RuntimeError('Another Molab request is active in this workspace; poll its existing handle.') from None
        try:
            yield
        finally:
            lock.seek(0)
            release()

def main():
    # Never abort a live remote stream on an unrepresentable Windows character.
    sys.stdout.reconfigure(errors='backslashreplace')
    sys.stderr.reconfigure(errors='backslashreplace')
    root = Path(__file__).resolve().parents[1]
    credentials = json.loads((root/'build/molab_pair.private.json').read_text())
    base = credentials['url'].rstrip('/')
    client = requests.Session()
    client.headers['Authorization'] = 'Bearer '+credentials['token']
    response = client.get(base+'/api/sessions', timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f'Session discovery HTTP {response.status_code}')
    sessions = response.json()
    if len(sessions) != 1:
        raise RuntimeError(f'Expected one session, found {len(sessions)}')
    code = Path(sys.argv[1]).read_text(encoding='utf-8')
    with client.post(base+'/api/kernel/execute', json={'code':code},
                     headers={'Marimo-Session-Id':next(iter(sessions))},
                     stream=True, timeout=(30, 60)) as stream:
        if stream.status_code != 200:
            raise RuntimeError(f'Execution HTTP {stream.status_code}')
        event = ''
        for line in stream.iter_lines(decode_unicode=True):
            if line.startswith('event:'):
                event = line[6:].strip()
            elif line.startswith('data:'):
                payload = json.loads(line[5:])
                if event in ('stdout','stderr'):
                    print(payload.get('data',''), end='', flush=True)
                elif event == 'done':
                    print(json.dumps({'execution_success':payload.get('success')}))
                    if not payload.get('success'):
                        raise RuntimeError('Remote execution failed')
                    return
        raise RuntimeError('SSE ended without done; inspect before retrying')

if __name__ == '__main__':
    try:
        with exclusive_execution(Path(__file__).resolve().parents[1]/'build/molab_execute.lock'):
            main()
    except requests.RequestException as exc:
        # Requests exception messages may include the credential-bearing URL.
        raise SystemExit(type(exc).__name__+' during Molab transport') from None
