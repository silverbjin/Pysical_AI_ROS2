"""Read completed numeric owner boundaries; never alter acceptance evidence."""
import hashlib,json,statistics,sys
from collections import defaultdict
from pathlib import Path
root=Path(sys.argv[1]);source=root/'controller_report.json'
closed=json.loads((root/'teardown.json').read_text())
assert closed['parent_reaped'] and not closed['residual_live_pids']
report=json.loads(source.read_text());fault=report['first_fault']
start=fault['phase_context']['_phase_start'] if fault else 0
end=fault['ros_ns'] if fault else 10**30
rows=[row for row in report['decision_cost_trace']
    if start<=row.get('decision_ros_ns',-1)<=end]
def stats(values):
    values=sorted(values)
    if not values:return dict(count=0)
    return dict(count=len(values),median_ns=statistics.median(values),
        mean_ns=statistics.mean(values),p95_ns=values[int((len(values)-1)*.95)],max_ns=max(values))
groups=defaultdict(lambda:defaultdict(list));details=[]
for row in rows:
    category=('published' if row['publication_after']>row['publication_before'] else 'held')
    if row['state']=='FAULT':category='fault'
    prior=row['started_wall_ns'];prior_cpu=row.get('started_thread_ns');costs={}
    model_origin=model_cpu_origin=None
    for stage in row['stages']:
        name,stamp=stage[:2]
        costs[name]=stamp-prior;groups[category][name].append(stamp-prior);prior=stamp
        if len(stage)==3 and prior_cpu is not None:
            costs[name+'_cpu']=stage[2]-prior_cpu
            groups[category][name+'_cpu'].append(stage[2]-prior_cpu);prior_cpu=stage[2]
        if name=='reference_rate':
            model_origin=stamp;model_cpu_origin=stage[2] if len(stage)==3 else None
        if name=='model' and model_origin is not None:
            costs['model_total']=stamp-model_origin
            groups[category]['model_total'].append(costs['model_total'])
            if model_cpu_origin is not None and len(stage)==3:
                costs['model_total_cpu']=stage[2]-model_cpu_origin
                groups[category]['model_total_cpu'].append(costs['model_total_cpu'])
    groups[category]['whole'].append(row['finished_wall_ns']-row['started_wall_ns'])
    if 'finished_thread_ns' in row:
        groups[category]['whole_cpu'].append(row['finished_thread_ns']-row['started_thread_ns'])
    details.append(dict(ros_ns=row['decision_ros_ns'],started_wall_ns=row['started_wall_ns'],
        category=category,reference_permitted=row.get('reference_permitted'),costs=costs))
value=dict(scope='post_reap_actual_numeric_boundaries_not_acceptance',trial=root.name,
    report_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    owner_pid=report['ingress_dispatch']['pid'],
    callback_native_tids=sorted({row['native_tid'] for row in rows if 'native_tid' in row}),
    ingress_native_tid=report['ingress_dispatch']['native_tid'],
    phase_start_ns=start,phase_end_ns=end,ring_rows=len(report['decision_cost_trace']),
    selected_rows=len(rows),first_selected_ros_ns=rows[0]['decision_ros_ns'] if rows else None,
    groups={key:{stage:stats(values) for stage,values in stages.items()} for key,stages in groups.items()},
    details=details,warning='Bounded ring may omit the beginning; wall differences include preemption. Optional _cpu fields are the same callback native thread CPU, not the entire process.')
out=root.parent/('analysis-decision-cost-'+root.name+'.json')
with out.open('x') as stream:json.dump(value,stream,indent=2)
preview={key:val for key,val in value.items() if key not in ('details','groups')}
preview['groups']={key:{stage:stages[stage] for stage in ('whole','whole_cpu','model','model_cpu','model_total','model_total_cpu','native_credit')
    if stage in stages} for key,stages in value['groups'].items()}
print(json.dumps(preview),flush=True)
