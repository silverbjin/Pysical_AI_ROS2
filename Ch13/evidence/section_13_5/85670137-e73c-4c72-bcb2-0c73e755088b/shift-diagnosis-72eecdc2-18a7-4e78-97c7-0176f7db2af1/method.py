"""Post-reap diagnosis; original records and failed verdict stay immutable."""
import hashlib,json,statistics,sys,uuid
from pathlib import Path

root=Path(sys.argv[1]);report_path=root/'controller_report.json'
teardown=json.loads((root/'teardown.json').read_text())
assert teardown['parent_reaped'] and not teardown['residual_live_pids']
report=json.loads(report_path.read_text());fault=report['first_fault']
start=fault['phase_context']['_phase_start'];end=fault['ros_ns']
pubs=[r for r in report['command_publications']['rows'] if start<=r['decision_ros_ns']<=end]
rows=[r for r in report['decision_cost_trace'] if start<=r.get('decision_ros_ns',-1)<=end]
gaps=[];last_ros=start;last_wall=None
for p in pubs:
    ros=p['decision_ros_ns'];wall=p['decision_wall_ns']
    interval=ros-last_ros
    wall_interval=None if last_wall is None else wall-last_wall
    eligible=interval if wall_interval is None else min(interval,wall_interval)
    gaps.append(dict(ros_ns=ros,ros_gap_ns=interval,wall_gap_ns=wall_interval,
        min_elapsed_ns=eligible,capped_40ms_ns=min(40_000_000,eligible),
        discarded_ns=max(0,eligible-40_000_000),
        computation_to_publish_ns=p['publish_started_ns']-wall))
    last_ros,last_wall=ros,wall
def stats(values):
    values=sorted(values)
    return (dict(count=0) if not values else dict(count=len(values),min=min(values),
        median=statistics.median(values),mean=statistics.mean(values),
        p95=values[int((len(values)-1)*.95)],max=max(values)))
metrics={}
with (root/'process_metrics.jsonl').open() as stream:
    for line in stream:
        sample=json.loads(line)
        if not pubs[0]['decision_wall_ns']-2_000_000_000<=sample['wall_ns']<=fault['wall_ns']+2_000_000_000:continue
        for p in sample['members']+[sample['observer'],sample['full_observer']]:
            key=(p['pid'],p['start_ticks']);ticks=p['user_ticks']+p['system_ticks']
            if key not in metrics:metrics[key]=dict(pid=p['pid'],identity=p.get('executable',p.get('scope','full_observer')),
                first_wall_ns=sample['wall_ns'],first_ticks=ticks)
            metrics[key].update(last_wall_ns=sample['wall_ns'],last_ticks=ticks,threads=p['threads'])
for p in metrics.values():
    duration=(p['last_wall_ns']-p['first_wall_ns'])/1e9
    p['cpu_core_equivalents']=(p['last_ticks']-p['first_ticks'])/100/duration if duration else None
summary=dict(scope='post_reap_original_failed_shift_not_acceptance',trial=root.name,
    controller_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
    fault=dict(reason=fault['reason'],ros_ns=end,wall_ns=fault['wall_ns'],**fault['phase_context']),
    phase_elapsed_ns=end-start,reference_clock=report['current']['crawl_shift_reference_clock'],
    publications=len(pubs),decision_count=len(rows),
    publication_intervals=stats([g['ros_gap_ns'] for g in gaps[1:]]),
    gaps_over_40ms=[g for g in gaps if g['discarded_ns']],
    discarded_sum_ns=sum(g['discarded_ns'] for g in gaps),
    original_cpu_ticks_per_s=100,process_metrics=list(metrics.values()),
    current_keys=list(report['current']),
    native_trace_keys=list(json.loads((root/'native_command_trace.json').read_text())),
    warning='40ms gap accounting is a publication-time proxy, not a reconstructed model state or new acceptance verdict.')
out=root.parent/('shift-diagnosis-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
(out/'result.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(dict(output=str(out),**summary)),flush=True)
