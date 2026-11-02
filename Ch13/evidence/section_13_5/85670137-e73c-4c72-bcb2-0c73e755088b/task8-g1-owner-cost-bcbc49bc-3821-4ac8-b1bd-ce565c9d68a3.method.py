"""Closed bounded traces and process summaries, no engine/raw-frame replay."""
import hashlib,json,statistics,uuid
from pathlib import Path
base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
names=['native-g1-gazebo-47892299-1722-4a76-acdb-942585899d39',
 'native-g1-gazebo-4187f73b-9cfb-4c0b-9e2e-586c48650f68',
 'native-g1-gazebo-7057d83b-0627-43da-9dd6-1b091822c61a']
out=dict(scope='closed_calibration_owner_cost_not_causal_or_new_engine_acceptance',trials=[])
for name in names:
    folder=base/name;p=folder/'controller_report.json';r=json.loads(p.read_text())
    snapshot=r['first_fault'] or r['current'];cal=snapshot['calibration'];start=cal['request']['wall_ns'];stages=cal['stages']
    finish=(r['first_fault'] or r['current'])['wall_ns'];costs={};total=[]
    for entry in r['decision_cost_trace']:
        if not start<=entry['started_wall_ns']<=finish:continue
        previous_wall,previous_cpu=entry['started_wall_ns'],entry['started_thread_ns']
        for key,wall,cpu in entry['stages']:
            costs.setdefault(key,[]).append((wall-previous_wall,cpu-previous_cpu));previous_wall,previous_cpu=wall,cpu
        total.append((entry.get('finished_wall_ns',previous_wall)-entry['started_wall_ns'],
            entry.get('finished_thread_ns',previous_cpu)-entry['started_thread_ns']))
    def summary(values):
        return dict(count=len(values),wall_total_ns=sum(v[0] for v in values),cpu_total_ns=sum(v[1] for v in values),
            median_wall_ns=statistics.median(v[0] for v in values),median_cpu_ns=statistics.median(v[1] for v in values),
            max_wall_ns=max(v[0] for v in values),max_cpu_ns=max(v[1] for v in values)) if values else None
    metrics=folder/'process_metrics.jsonl';procs={}
    for line in metrics.read_text().splitlines():
        row=json.loads(line)
        if not start<=row['wall_ns']<=finish:continue
        members=list(row['members'])
        for extra in ('observer','full_observer'):
            if row.get(extra):members.append(dict(row[extra],executable=extra))
        for member in members:
            data=procs.setdefault(member['pid'],dict(command=member['executable'],samples=[]))
            data['samples'].append((row['wall_ns'],member['user_ticks']+member['system_ticks'],member['threads']))
    cpu=[]
    for pid,v in procs.items():
        first,last=v['samples'][0],v['samples'][-1];elapsed=(last[0]-first[0])/1e9
        if elapsed>1.:cpu.append(dict(pid=pid,command=v['command'],average_cpu_one_core_percent=(last[1]-first[1])/elapsed,
            max_threads=max(x[2] for x in v['samples'])))
    out['trials'].append(dict(trial=name,report_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        metrics_sha256=hashlib.sha256(metrics.read_bytes()).hexdigest(),fault=None if not r['first_fault'] else r['first_fault']['reason'],
        request=cal['request'],vertical_remaining_wall_ns=None if not cal['vertical'] else cal['vertical']['remaining_wall_ns'],
        stage_costs=[dict(phase=a['phase'],next_phase=b['phase'],ros_s=(b['ros_ns']-a['ros_ns'])/1e9,
            wall_s=(b['wall_ns']-a['wall_ns'])/1e9,ratio=(b['ros_ns']-a['ros_ns'])/(b['wall_ns']-a['wall_ns'])) for a,b in zip(stages,stages[1:])],
        owner_total=summary(total),owner_stages={k:summary(v) for k,v in costs.items()},
        process_cpu=sorted(cpu,key=lambda x:-x['average_cpu_one_core_percent'])))
output=base/('task8-g1-owner-cost-'+str(uuid.uuid4())+'.json');assert not output.exists()
out['method_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();output.write_text(json.dumps(out,indent=2))
output.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(output),trials=[dict(trial=v['trial'],fault=v['fault'],stage_costs=v['stage_costs'],
    owner_total=v['owner_total'],owner_stage_cpu_ms={k:round(a['cpu_total_ns']/1e6,3) for k,a in v['owner_stages'].items()},
    top_cpu=v['process_cpu'][:6]) for v in out['trials']]),indent=2))
