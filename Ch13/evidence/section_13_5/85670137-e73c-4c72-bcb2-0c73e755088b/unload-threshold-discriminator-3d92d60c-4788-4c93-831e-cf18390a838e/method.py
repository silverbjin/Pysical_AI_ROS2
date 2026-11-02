"""Closed real-contact trace: threshold crossings and dwell, never acceptance."""
from pathlib import Path
import hashlib,json,uuid,sys
base=Path.cwd()/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial=base/(sys.argv[1] if len(sys.argv)>1 else 'native-g2-gazebo-b9c835b2-0b3d-4365-a56e-3dc7a9a65ce7')
assert trial.parent==base and trial.name.startswith('native-g2-gazebo-')
closed=json.loads((trial/'teardown.json').read_text());assert closed['parent_reaped'] and not closed['residual_live_pids']
fault=json.loads((trial/'controller_report.json').read_text())['first_fault']
foot=fault['state_before']['swing_foot'];start=fault['phase_context']['_unload_start'];end=fault['ros_ns']
path=trial/'mission_probe/observations.jsonl';samples={}
for line in path.open():
    row=json.loads(line)
    if row['kind']!='contacts':continue
    v=row['value'];stamp=v['stamp_ns']
    if start<=stamp<=end:
        i=v['data']['names'].index(foot)
        samples.setdefault(stamp,dict(ros_ns=stamp,received_ns=v['received_ns'],force_n=v['data']['forces'][i]))
rows=sorted(samples.values(),key=lambda r:r['ros_ns']);crossings=[];runs=[];run=None;previous=None
for r in rows:
    below=r['force_n']<2.
    if previous is not None and (previous['force_n']<2.)!=below:crossings.append(r)
    if below and run is None:run=r['ros_ns']
    if not below and run is not None:runs.append(dict(start=run,end=r['ros_ns'],below_ns=r['ros_ns']-run));run=None
    previous=r
if run is not None:runs.append(dict(start=run,end=rows[-1]['ros_ns'],below_ns=rows[-1]['ros_ns']-run))
out=base/('unload-threshold-discriminator-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
value=dict(scope='independent_contact_observer_not_exact_controller_selected_cache',trial=trial.name,
    input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),foot=foot,start_ros_ns=start,end_ros_ns=end,
    unique_captures=len(rows),minimum_force_n=min((r['force_n'] for r in rows),default=None),
    maximum_force_n=max((r['force_n'] for r in rows),default=None),crossings=crossings,
    below_runs=runs,rows=rows,caveats=['callback selection differs from controller; infer no exact eligibility from this observer alone'])
(out/'result.json').write_text(json.dumps(value,indent=2,allow_nan=False))
print(json.dumps(dict(output=str(out),unique_captures=len(rows),minimum=value['minimum_force_n'],maximum=value['maximum_force_n'],
    crossings=len(crossings),longest_below_ns=max((r['below_ns'] for r in runs),default=0),last_crossings=crossings[-8:])),flush=True)
