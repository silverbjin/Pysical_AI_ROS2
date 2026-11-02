"""Bounded postmortem: correlate the first fault with auxiliary trace spans."""
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);target=Path(sys.argv[2])
assert not target.exists()
report=json.loads((p/'controller_report.json').read_text())
events=[json.loads(line) for line in (p/'control_clock.jsonl').open()]
closed=next(r for r in events if r['event']=='closed')
fault=next(r for r in events if r['event']=='fault')
spans=closed['publication_work']['rows']
span=max(spans,key=lambda r:r['trace_finished_wall_ns']-r['trace_started_wall_ns'])
rows=closed['input_transport']['rows'];start=span['trace_started_wall_ns'];end=span['trace_finished_wall_ns']
before=[r for r in rows if r['received_wall_ns']<=start][-1]
after=next(r for r in rows if r['received_wall_ns']>=end)
first=report['first_fault'];pending=first['pending_capture_receipts']
data=dict(scope='closed_trial_diagnostic_not_acceptance',trial=p.name,
 inputs={name:hashlib.sha256((p/name).read_bytes()).hexdigest() for name in ('controller_report.json','control_clock.jsonl','result.json')},
 method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 trace_span=span,trace_wall_ms=(end-start)/1e6,first_crawl_fault=dict(reason=first['reason'],ros_ns=first['ros_ns'],wall_ns=first['wall_ns']),
 selected_imu={k:v for k,v in first['samples']['imu'].items() if k!='data'},
 pending_imu=pending['imu'],pending_body=pending['body'],pending_contacts=pending['contacts'],
 relay_fault=fault,before_trace_input=before,next_callback_after_trace=after,
 claim='Trace phase stalled shared executor while other sensor ingress continued. Wall span includes scheduling; exact write syscall duration and disk-only causality not established.',
 next_experiment='Inject delayed sink; bound queue and isolate file writes from sole clock executor; retain all original clock/safety/close checks.')
target.write_text(json.dumps(data,indent=2));print(json.dumps(dict(path=str(target),trace_wall_ms=data['trace_wall_ms'],reason=first['reason'])))
