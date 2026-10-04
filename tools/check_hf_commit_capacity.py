"""HF history admission checks: execute only in MoLab, no uploads."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from datetime import datetime, timezone
from types import SimpleNamespace
import hf_artifact_archive as a
import json

now = 100000.0
assert a._capacity_from_dates([], now, 3)['admitted']
assert a._capacity_from_dates([now-1]*117, now, 3)['admitted']
blocked = a._capacity_from_dates([now-1]*118, now, 3)
assert not blocked['admitted'] and blocked['wait_seconds'] == 3604
assert a._capacity_from_dates([now-3600]*128, now, 3)['admitted']
blocked = a._capacity_from_dates([now-3500]*20+[now-1]*110, now, 3)
assert not blocked['admitted'] and blocked['wait_seconds'] == 105
assert a._capacity_from_dates([now-1]*120, now, 1)['admitted'] is False
for need in (0, 121, -1, 1.5):
    try: a._capacity_from_dates([], now, need)
    except ValueError: pass
    else: raise AssertionError('invalid required commits admitted')

class Fake:
    def list_repo_commits(self, repo, **kwargs):
        assert repo == 'TryDotAtwo/faithful-fly-artifacts'
        return [SimpleNamespace(created_at=datetime.fromtimestamp(now-1,timezone.utc))]*120
try: a.require_commit_capacity(Fake(),'TryDotAtwo/faithful-fly-artifacts',1,now=now)
except a.ArchiveCapacityError: pass
else: raise AssertionError('saturated history admitted')
print(json.dumps({'quota_admission_checks':'passed','network_upload_tested':False,
'checks':['capacity reserve before experiment','soft limit reserves eight observed server slots',
'old commits expire','wait uses sufficient expirations rather than first only',
'bad requested capacity rejected','saturated API history stops admission'],
'limitations':['estimate is not a reservation','failed requests absent from Git history',
'concurrent publishers can change quota','server 429 still stops progression']}))
