"""Numeric snapshot taken BEFORE its read-only report request; no live sampling."""
import hashlib,json,statistics,sys
from collections import defaultdict
from pathlib import Path
source=Path(sys.argv[1]).resolve()
report=json.loads(source.read_text());groups=defaultdict(lambda:defaultdict(list))
details=[]
for row in report['decision_cost_trace']:
    category='published' if row['publication_after']>row['publication_before'] else 'held'
    previous=row['started_wall_ns'];cpu=row['started_thread_ns'];costs={}
    for name,wall_stamp,cpu_stamp in row['stages']:
        groups[category][name].append((wall_stamp-previous,cpu_stamp-cpu))
        costs[name]=[wall_stamp-previous,cpu_stamp-cpu]
        previous,cpu=wall_stamp,cpu_stamp
    details.append(dict(ros_ns=row['decision_ros_ns'],category=category,costs=costs))
def stats(values):
    return dict(count=len(values),wall_median_ms=statistics.median(v[0] for v in values)/1e6,
        cpu_median_ms=statistics.median(v[1] for v in values)/1e6,
        wall_max_ms=max(v[0] for v in values)/1e6,cpu_max_ms=max(v[1] for v in values)/1e6)
value=dict(scope='original_numeric_ring_before_report_request_not_native_acceptance',
    source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    report_ros_ns=report['current']['ros_ns'],report_state=report['current']['state'],
    model_stages={key:{name:stats(values) for name,values in stages.items() if name.startswith('model_')}
        for key,stages in groups.items()},details=details)
out=Path(__file__).with_name('result.json')
with out.open('x') as stream:json.dump(value,stream,indent=2)
print(json.dumps({key:value for key,value in value.items() if key!='details'}))
