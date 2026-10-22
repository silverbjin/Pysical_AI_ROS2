"""Read-only capture/worker chronology around an explicitly selected wall window."""
import json
from pathlib import Path
import sys

folder, start, end = Path(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
observation = json.loads((folder/'observations.json').read_text())
rows = []
for line in (folder/'trace.jsonl').read_text().splitlines():
    r = json.loads(line)['record']
    t = r['times_ns']
    if any(start <= value/1e9 <= end for value in t.values()):
        rows.append(dict(stage=r['stage'], capture=r['capture_ns'], outcome=r['outcome'],
                         ros_now=r['ros_now_ns'], times={k:round(v/1e9,6) for k,v in t.items()}))
for r in observation.get('diagnostics', []):
    wall = r.get('wall', r.get('emitted_monotonic', r.get('monotonic_ns', 0)/1e9))
    # Candidate records carry monotonic_ns; detector ingress uses received_ns.
    wall = wall or r.get('received_ns', 0)/1e9
    if start <= wall <= end:
        rows.append(dict(diagnostic=r))
print(json.dumps(dict(window=[start,end], rows=rows), indent=2))
