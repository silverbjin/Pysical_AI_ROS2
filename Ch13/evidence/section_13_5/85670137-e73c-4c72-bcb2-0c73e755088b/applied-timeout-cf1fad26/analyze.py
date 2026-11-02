"""Post-reap exact 12-joint target match, separate from ACK wire receipt."""
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
closed=json.loads((root/'teardown.json').read_text())
assert closed['parent_reaped'] and not closed['residual_live_pids']
report_path=root/'controller_report.json';trace_path=root/'native_command_trace.json'
r=json.loads(report_path.read_text());trace=json.loads(trace_path.read_text())
credit=r['current']['applied_reference_credit']
pending=next(row for row in reversed(credit['events']) if row['event']=='abandoned_for_stop')
names=r['command_publications']['joint_names'];indices=[trace['joints'].index(name) for name in names]
publications=[row for row in r['command_publications']['rows']
    if row['values']==pending['values'] and row['decision_ros_ns']==pending['issued_ros_ns']]
assert len(publications)==1
published=publications[0]
details={}
for kind in ('cm_write','pre_step'):
    rows=trace[kind]['rows']
    matching=[row for row in rows if [row['ctrl'][i] for i in indices]==pending['values']]
    after=[row for row in matching if row['snapshot_ros_ns']>=pending['issued_ros_ns']]
    window=[row for row in rows if pending['issued_ros_ns']-10_000_000<=row['snapshot_ros_ns']
        <=pending['issued_ros_ns']+250_000_000]
    def brief(row):
        return {key:row[key] for key in ('sequence','snapshot_ros_ns','steady_ns')}
    details[kind]=dict(total=len(rows),matching_count=len(matching),matching_after_issue=len(after),
        first_matching=brief(matching[0]) if matching else None,
        first_matching_after_issue=brief(after[0]) if after else None,
        publication_to_first_after_wall_ns=after[0]['steady_ns']-published['publish_started_ns'] if after else None,
        window=[dict(**brief(row),legs=[row['ctrl'][i] for i in indices]) for row in window])
value=dict(scope='exact_native_target_application_not_client_ACK_delivery_or_acceptance',
    trial=root.name,report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
    trace_sha256=hashlib.sha256(trace_path.read_bytes()).hexdigest(),
    method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    first_fault_record=r['first_fault'],first_stop={key:r['first_stop'][key] for key in ('reason','ros_ns','wall_ns')},
    abandoned_pending=pending,publication=published,native=details)
with Path(__file__).with_name('result.json').open('x') as stream:json.dump(value,stream,indent=2)
preview={key:val for key,val in value.items() if key not in ('publication','native')}
preview['native']={key:{k:v for k,v in val.items() if k!='window'} for key,val in details.items()}
print(json.dumps(preview))
