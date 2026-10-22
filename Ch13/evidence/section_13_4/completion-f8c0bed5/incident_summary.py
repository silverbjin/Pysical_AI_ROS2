"""Compact observed latency chain at the first post-enable safety gate loss."""
import json
from pathlib import Path
import sys

folder = Path(sys.argv[1])
result = json.loads((folder/'result.json').read_text())
observation = json.loads((folder/'observations.json').read_text())
started = result['tracking_session']['requested_monotonic']
failure = next((r for r in observation['tracking'] if r['emitted_monotonic'] >= started
                and r.get('event') == 'disabled' and r.get('reason') != 'operator disabled'), None)
if failure is None:
    print(json.dumps(dict(status=result['status'], errors=result['errors'])))
    raise SystemExit(0)
wall=failure['emitted_monotonic']
print(json.dumps(dict(status=result['status'], reason=failure['reason'], wall=wall,
                     inputs=failure['inputs']),indent=2))
for r in observation.get('diagnostics',[]):
    if wall-.4 <= r.get('wall',0) <= wall+.1 and (r.get('status') not in
            ('CANDIDATE','INPUT_RECEIVED','QUEUED','DETECTED') or
            r.get('event') in ('EXPIRED_OR_OLD','BUNDLE_NOT_CURRENT','WORKER_DONE')):
        print(json.dumps(dict(diagnostic=r)))
for r in observation.get('tracks',[]):
    if wall-.4 <= r.get('wall',0) <= wall+.1:
        print(json.dumps(dict(track=r)))
for line in (folder/'trace.jsonl').read_text().splitlines():
    r=json.loads(line)['record']
    t=r['times_ns']
    if not any(wall-.8 <= v/1e9 <= wall+.15 for v in t.values()):
        continue
    if r['stage']=='tracking' and r['outcome']=='NO_COMMAND':
        continue
    print(json.dumps(dict(stage=r['stage'],capture=r['capture_ns'],outcome=r['outcome'],
                         ros_now=r['ros_now_ns'],times={k:round(v/1e9,6) for k,v in t.items()})))
