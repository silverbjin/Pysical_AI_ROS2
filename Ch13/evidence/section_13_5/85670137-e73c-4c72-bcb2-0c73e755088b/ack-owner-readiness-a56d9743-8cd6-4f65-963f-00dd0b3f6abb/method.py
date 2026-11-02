"""Closed original decision/ACK boundaries; does not synthesize permission."""
import hashlib,json,statistics,sys,uuid
from pathlib import Path

root=Path(sys.argv[1]).resolve(strict=True)
t=json.loads((root/'teardown.json').read_text())
assert t['parent_reaped'] and not t['residual_live_pids']
c=json.loads((root/'controller_report.json').read_text())
f=c['first_fault'];start=f['phase_context']['_phase_start'];end=f['ros_ns']
decisions=[x for x in c['decision_cost_trace'] if start<=x.get('decision_ros_ns',0)<=end]
pubs=[x for x in c['command_publications']['rows'] if start<=x['decision_ros_ns']<=end]
acks=[x for x in c['current']['applied_reference_credit']['events'] if x['event']=='applied']
rows=[]
for a in acks:
    ds=[d for d in decisions if a['issued_wall_ns']<=d['started_wall_ns']<=a['confirmed_wall_ns']]
    eligible=[d for d in ds if a['received_ns']<=d['started_wall_ns'] and a['stamp_ns']<=d['decision_ros_ns']]
    rows.append(dict(issued_ros_ns=a['issued_ros_ns'],capture_ros_ns=a['stamp_ns'],
        issued_wall_ns=a['issued_wall_ns'],first_receipt_wall_ns=a['received_ns'],
        confirmed_wall_ns=a['confirmed_wall_ns'],confirmed_ros_ns=a['confirmed_ros_ns'],
        receive_after_publish_ns=a['received_ns']-a['issued_wall_ns'],
        confirmation_after_receipt_ns=a['confirmed_wall_ns']-a['received_ns'],
        first_eligible_decision_wall_ns=eligible[0]['started_wall_ns'] if eligible else None,
        decisions=[dict(ros_ns=d['decision_ros_ns'],wall_ns=d['started_wall_ns'],
            finished_wall_ns=d['finished_wall_ns'],reference_permitted=d.get('reference_permitted'),
            publishes=d['publication_after']>d['publication_before'],
            ack_received=a['received_ns']<=d['started_wall_ns'],
            capture_eligible=a['stamp_ns']<=d['decision_ros_ns']) for d in ds]))
def stats(xs):
    return dict(count=len(xs),mean_ns=statistics.mean(xs),median_ns=statistics.median(xs),min_ns=min(xs),max_ns=max(xs)) if xs else dict(count=0)
result=dict(scope='original_owner_ack_readiness_no_synthetic_acceptance',trial=root.name,
    controller_sha256=hashlib.sha256((root/'controller_report.json').read_bytes()).hexdigest(),
    phase=[start,end],original_dispatch=c['current']['reference_dispatch'],
    publications=len(pubs),decisions=len(decisions),events=rows,
    ack_receipt_latency=stats([x['receive_after_publish_ns'] for x in rows]),
    ack_confirmation_latency=stats([x['confirmation_after_receipt_ns'] for x in rows]),
    eligible_but_not_permitted=[x for x in rows if any(d['ack_received'] and d['capture_eligible'] and not d['reference_permitted'] for d in x['decisions'])],
    warning='Bounded last 32 credit events only. Wall decision start precedes original ROS read by a small interval. Untraced ingress notifications cannot be inferred.')
out=root.parent/('ack-owner-readiness-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
(out/'result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(output=str(out),**{k:v for k,v in result.items() if k not in ('events','eligible_but_not_permitted','warning')}),indent=2))
for row in rows[-8:]:print(json.dumps(row))
