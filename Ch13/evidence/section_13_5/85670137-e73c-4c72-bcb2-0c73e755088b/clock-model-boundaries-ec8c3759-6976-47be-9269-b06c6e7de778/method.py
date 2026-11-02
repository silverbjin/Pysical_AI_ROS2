"""Closed-trial original clock boundaries; no synthetic acceptance verdict."""
import hashlib,json,statistics,sys,uuid
from pathlib import Path

root=Path(sys.argv[1]).resolve(strict=True)
closed=json.loads((root/'teardown.json').read_text())
assert closed['parent_reaped'] and closed['residual_live_pids']==[]
controller=json.loads((root/'controller_report.json').read_text());fault=controller['first_fault']
start=fault['phase_context']['_phase_start'];end=fault['ros_ns']
calibration=fault.get('calibration') or {};request=calibration.get('request') or {}
wall_start=request.get('wall_ns',fault['wall_ns']-5_000_000_000);wall_end=fault['wall_ns']
pubs=[row for row in controller['command_publications']['rows'] if start<=row['decision_ros_ns']<=end]
events=[]
with (root/'control_clock.jsonl').open() as stream:
    for line in stream:events.append(json.loads(line))
final=next(row for row in reversed(events) if row.get('event')=='closed')
clock=[row for row in events if row.get('event')=='publish' and start<=row['capture_ns']<=end]
inputs=[row for row in final['input_transport']['rows'] if wall_start<=row['received_wall_ns']<=wall_end]
work=[row for row in final['publication_work']['rows'] if wall_start<=row['publish_started_wall_ns']<=wall_end]

def stats(values):
    values=sorted(values)
    return dict(count=0) if not values else dict(count=len(values),median_ns=statistics.median(values),
        mean_ns=statistics.mean(values),p95_ns=values[int((len(values)-1)*.95)],max_ns=max(values),min_ns=min(values))
def gaps(rows,key):return [b[key]-a[key] for a,b in zip(rows,rows[1:])]
window=calibration.get('shift_reference_clock') or controller['current'].get('crawl_shift_reference_clock')
cap=window.get('max_step_ns',window['nominal_step_ns']) if window else 20_000_000
loss=[]
for a,b in zip(pubs,pubs[1:]):
    ros=b['decision_ros_ns']-a['decision_ros_ns'];wall=b['decision_wall_ns']-a['decision_wall_ns']
    loss.append(dict(ros_ns=b['decision_ros_ns'],ros_delta_ns=ros,wall_delta_ns=wall,
        min_elapsed_ns=min(ros,wall),capped_elapsed_ns=min(cap,ros,wall),discarded_ns=max(0,min(ros,wall)-cap)))
report=dict(scope='original_closed_trial_clock_model_boundaries_not_acceptance',trial=root.name,
    controller_sha256=hashlib.sha256((root/'controller_report.json').read_bytes()).hexdigest(),
    control_clock_sha256=hashlib.sha256((root/'control_clock.jsonl').read_bytes()).hexdigest(),
    phase=dict(start_ros_ns=start,end_ros_ns=end,elapsed_ns=end-start,**fault['phase_context']),
    calibration=calibration,reference_clock=window,reference_cap_ns=cap,command_publications=len(pubs),
    cap_source='max_step_ns' if window and 'max_step_ns' in window else 'nominal_step_ns',
    command_ros_gaps=stats(gaps(pubs,'decision_ros_ns')),command_wall_gaps=stats(gaps(pubs,'decision_wall_ns')),
    clock_publications=len(clock),clock_capture_gaps=stats(gaps(clock,'capture_ns')),
    clock_publish_gaps=stats(gaps(clock,'published_wall_ns')),
    input_receipts=len(inputs),input_ring_capacity=final['input_transport']['capacity'],
    input_first_wall_ns=inputs[0]['received_wall_ns'] if inputs else None,
    input_last_wall_ns=inputs[-1]['received_wall_ns'] if inputs else None,
    rmw_transport=stats([row['rmw_received_system_ns']-row['source_system_ns'] for row in inputs
        if row['rmw_received_system_ns']>0 and row['source_system_ns']>0]),
    callback_after_rmw=stats([row['callback_system_ns']-row['rmw_received_system_ns'] for row in inputs if row['rmw_received_system_ns']>0]),
    trace_work=stats([row['trace_finished_wall_ns']-row['trace_started_wall_ns'] for row in work]),
    publish_work=stats([row['publish_finished_wall_ns']-row['publish_started_wall_ns'] for row in work]),
    actual_publish_start_gaps=stats(gaps(work,'publish_started_wall_ns')),
    command_gap_cap_proxy=sum(row['discarded_ns'] for row in loss),command_intervals=loss,
    model_tick_spans=fault.get('tick_spans'),clock_read_span=fault.get('clock_read_span'),
    decision_cost_current=fault.get('decision_cost_current'),ingress=controller.get('ingress_dispatch'),
    decision_trace_rows=len(controller.get('decision_cost_trace') or []),
    warning='Separate SYSTEM/MONO/RAW domains remain separate. Publication gap caps are a proxy, not reconstruction of per-tick reference state. No trace rows does not prove absent callbacks.')
out=root.parent/('clock-model-boundaries-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
(out/'result.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(output=str(out),**{key:value for key,value in report.items()
    if key not in ('command_intervals','model_tick_spans','decision_cost_current','ingress','warning')}),indent=2))
