"""Closed original relay intervals; no input-continuity inference from missing trace."""
import hashlib,json,statistics,sys,uuid
from pathlib import Path
root=Path(sys.argv[1]);outbase=Path(sys.argv[2]);closed=json.loads((root/'teardown.json').read_text())
assert closed['parent_reaped'] and not closed['residual_live_pids']
report=json.loads((root/'controller_report.json').read_text());fault=report['first_fault']
phase=fault['phase_context']['_phase_start'];a=next(r['started_wall_ns'] for r in report['decision_cost_trace'] if r.get('decision_ros_ns')==phase)
b=fault['wall_ns'];rows=[];source=root/'control_clock.jsonl'
with source.open() as stream:
    for line in stream:
        row=json.loads(line)
        if row.get('event')=='publish' and a<=row['published_wall_ns']<=b:rows.append(row)
gaps=[dict(wall_gap_ns=y['published_wall_ns']-x['published_wall_ns'],capture_gap_ns=y['capture_ns']-x['capture_ns'],
    input_count_delta=y['inputs']-x['inputs'],latest_input_age_ns=y['published_wall_ns']-y['received_wall_ns'],
    previous_input_age_ns=x['published_wall_ns']-x['received_wall_ns'],published_wall_ns=y['published_wall_ns']) for x,y in zip(rows,rows[1:])]
def stats(values):
    v=sorted(values);return dict(count=len(v),median=statistics.median(v),mean=statistics.mean(v),p95=v[int((len(v)-1)*.95)],max=max(v))
result=dict(scope=__doc__,trial=root.name,phase_start_ns=phase,wall_interval_ns=b-a,
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),publications=len(rows),
    wall_gap=stats([r['wall_gap_ns'] for r in gaps]),latest_input_age=stats([r['latest_input_age_ns'] for r in gaps]),
    worst_intervals=sorted(gaps,key=lambda r:r['wall_gap_ns'],reverse=True)[:10],
    warning='Input counter deltas prove received callbacks only; their within-gap distribution and original physics pacing are not reconstructed.')
out=outbase/('relay-window-'+str(uuid.uuid4()));out.mkdir();(out/'method.py').write_bytes(Path(__file__).read_bytes())
(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(output=str(out),**result)))
