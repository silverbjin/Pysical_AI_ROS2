"""Compare two closed G1 reports; no new trial or runtime mutation."""
import sys,json,hashlib,statistics
from pathlib import Path
base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
names=['native-g1-gazebo-027edf99-68f1-452c-9434-578b6f8602d7','native-g1-gazebo-330b055b-0cb9-4db5-872d-06e2613fe447']
out=dict(scope='closed_G1_deadline_comparison_not_new_engine',trials=[])
for name in names:
    folder=base/name;report_path=folder/'controller_report.json';r=json.loads(report_path.read_text())
    frame=r['first_fault'] or r['current'];cal=frame['calibration'];request=cal['request'];stages=cal['stages']
    entry=dict(trial=name,report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
        first_fault=None if not r['first_fault'] else r['first_fault']['reason'],
        calibration_request=request,stages=stages,vertical=cal['vertical'],
        stage_costs=[dict(phase=a['phase'],next_phase=b['phase'],
            ros_s=(b['ros_ns']-a['ros_ns'])/1e9,wall_s=(b['wall_ns']-a['wall_ns'])/1e9,
            ratio=(b['ros_ns']-a['ros_ns'])/(b['wall_ns']-a['wall_ns'])) for a,b in zip(stages,stages[1:])])
    metrics=folder/'process_metrics.jsonl';rows=[json.loads(line) for line in metrics.read_text().splitlines()]
    procs={}
    for row in rows:
        members=list(row['members'])
        for extra in ('observer','full_observer'):
            if row.get(extra):members.append(dict(row[extra],executable=extra))
        for member in members:
            key=member['pid'];item=procs.setdefault(key,dict(executable=member['executable'],points=[],threads=[]))
            item['points'].append((row['wall_ns'],member['user_ticks']+member['system_ticks']))
            item['threads'].append(member['threads'])
    table=[]
    for pid,item in procs.items():
        first,last=item['points'][0],item['points'][-1];elapsed=(last[0]-first[0])/1e9
        if elapsed>1.:table.append(dict(pid=pid,command=item['executable'],
            average_cpu_one_core_percent=(last[1]-first[1])/elapsed,
            threads_max=max(item['threads']),observed_wall_s=elapsed))
    entry['cpu']=sorted(table,key=lambda a:-a['average_cpu_one_core_percent'])
    entry['metrics_sha256']=hashlib.sha256(metrics.read_bytes()).hexdigest();out['trials'].append(entry)
out['method_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
output=base/'task8-g1-deadline-comparison-01.json';assert not output.exists();output.write_text(json.dumps(out,indent=2))
method=output.with_suffix('.method.py');assert not method.exists();method.write_bytes(Path(__file__).read_bytes())
print(json.dumps(out,indent=2))
