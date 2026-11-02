"""Positive independent original /clock witnesses inside relay output gaps."""
import hashlib,json,sys,uuid
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'Ch13/scripts'))
from native_observer_13_5 import read_records
root=Path(sys.argv[1]);base=Path(sys.argv[2]);closed=json.loads((root/'teardown.json').read_text())
assert closed['parent_reaped'] and not closed['residual_live_pids']
report=json.loads((root/'controller_report.json').read_text());fault=report['first_fault']
phase=fault['phase_context']['_phase_start'];start=next(r['started_wall_ns'] for r in report['decision_cost_trace'] if r.get('decision_ros_ns')==phase)
end=fault['wall_ns'];frames=[];digest=hashlib.sha256();rows=[]
class HashedReader:
    def __init__(self,stream):self.stream=stream
    def read(self,count):
        data=self.stream.read(count);digest.update(data);return data
with (root/'observations.cdr').open('rb') as stream:
    for row in read_records(HashedReader(stream)):
        meta=row['meta']
        if meta['kind']=='frame' and start-100_000_000<=meta['wall_ns']<=end:
            frames.append(meta)
with (root/'control_clock.jsonl').open() as stream:
    for line in stream:
        row=json.loads(line)
        if row.get('event')=='publish' and start-100_000_000<=row['published_wall_ns']<=end:rows.append(row)
gaps=[]
for a,b in zip(rows,rows[1:]):
    interval=b['published_wall_ns']-a['published_wall_ns']
    if interval<=25_000_000:continue
    witnesses=[dict(wall_ns=f['wall_ns'],ros_ns=f['ros_ns'],ahead_of_previous_relay_ns=f['ros_ns']-a['capture_ns'],
        before_next_relay_by_ns=b['published_wall_ns']-f['wall_ns']) for f in frames
        if a['published_wall_ns']<f['wall_ns']<b['published_wall_ns'] and f['ros_ns']>a['capture_ns']]
    gaps.append(dict(relay_gap_ns=interval,previous_relay_capture_ns=a['capture_ns'],
        next_relay_capture_ns=b['capture_ns'],next_relay_wall_ns=b['published_wall_ns'],
        input_count_delta=b['inputs']-a['inputs'],independent_original_clock_witnesses=witnesses))
value=dict(scope=__doc__,original_trial=root.name,original_cdr_sha256=digest.hexdigest(),
    phase_start_ns=phase,phase_end_ns=fault['ros_ns'],independent_frames=len(frames),gaps_over25ms=len(gaps),
    gaps_with_positive_clock_witness=sum(bool(row['independent_original_clock_witnesses']) for row in gaps),
    gaps=sorted(gaps,key=lambda row:row['relay_gap_ns'],reverse=True),
    limitation='Positive receipt of advancing original global ROS time in an independent native process only. Does not prove relay input callback times or separate middleware from relay executor scheduling.')
out=base/('independent-clock-witness-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes());(out/'result.json').write_text(json.dumps(value,indent=2))
print(json.dumps(dict(output=str(out),**{k:v for k,v in value.items() if k!='gaps'},largest_gap=value['gaps'][:2])))
