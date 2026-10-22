"""Capture-window context, never an approximate latency join."""
import json
import os
from pathlib import Path
root = Path(os.environ['CH13_EGL_EVIDENCE'])
output = root/'gate-neighbors.json'
if output.exists():
    raise FileExistsError(output)
contexts = []
for label in ('m10a','m10b','m10c','m15a','m15b','m15c'):
    folder = root/label
    summary = json.loads((folder/'trace_summary.json').read_text())
    records = [json.loads(v)['record'] for v in (folder/'trace.jsonl').read_text().splitlines()]
    for loss in summary['gate_losses']:
        if loss['capture_ns'] is None or loss['ros_age_ns'] is None:
            continue
        upper = loss['capture_ns']+loss['ros_age_ns']+100_000_000
        selected = [v for v in records if v['stage'] != 'tracking' and
                    v['capture_ns'] is not None and loss['capture_ns'] <= v['capture_ns'] <= upper]
        selected.sort(key=lambda v:(v['capture_ns'],v['stage']))
        contexts.append(dict(label=label,loss=loss,records=selected,
            note='Capture window from last valid target to observed loss ROS time +100ms. '
                 'This is context selection, NOT nearest-capture joining or steady-state coverage proof.'))
        if label in ('m10a','m15a'):
            for value in selected:
                print(json.dumps(dict(label=label,capture_ns=value['capture_ns'],stage=value['stage'],
                    outcome=value['outcome'],ros_age_ms=(value['ros_now_ns']-value['capture_ns'])/1e6
                    if value['ros_now_ns'] is not None else None)))
output.write_text(json.dumps(contexts,indent=2)+'\n')
