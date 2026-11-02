"""Bounded closed-trial contact/command discriminator from original JSONL."""
from pathlib import Path
import hashlib,json,math,sys,uuid

base=Path.cwd()/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
name=sys.argv[1];trial=base/name
assert trial.parent==base and name.startswith('native-g2-gazebo-')
closed=json.loads((trial/'teardown.json').read_text())
assert closed['parent_reaped'] and not closed['residual_live_pids']
report=json.loads((trial/'controller_report.json').read_text());fault=report['first_fault']
assert fault is not None
end=fault['ros_ns'];start=fault['phase_context']['_unload_start']
path=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/name/'observations.jsonl'
digest=hashlib.sha256();packets=0;rows=[];nearest=None;early=None;last=None
with path.open('rb') as source:
    for line in source:
        digest.update(line)
        if b'"native_controls"' not in line[:100]:continue
        record=json.loads(line)
        if record['kind']!='native_controls':continue
        packet=record['value'];packets+=1
        if nearest is None or abs(packet['capture_ns']-end)<abs(nearest['capture_ns']-end):nearest=packet
        for body in packet.get('body_references',[]):
            stamp=body['capture_ns']
            if not start<=stamp<=end:continue
            if last is not None and stamp-last<20_000_000:continue
            last=stamp
            rows.append(dict(capture_ns=stamp,feet=[dict(name=f['name'],valid=f['force_on_collision_valid'],
                force=f['sum_force_on_collision_world_n']) for f in body['raw_contacts']['feet']]))
assert packets and rows
out=base/('spatial-contact-discriminator-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
statistics={}
for foot in rows[0]['feet']:
    values=[f['force'] for row in rows for f in row['feet'] if f['name']==foot['name'] and f['valid']]
    statistics[foot['name']]=dict(captures=len(values),last_force_world_n=values[-1],
        maximum_tangential_n=max(math.hypot(*v[:2]) for v in values),
        maximum_normal_abs_n=max(abs(v[2]) for v in values),
        maximum_tangent_over_normal=max(math.hypot(*v[:2])/abs(v[2]) for v in values if abs(v[2])>=2))
value=dict(scope='raw_collision_force_summary_not_ground_deduplicated_acceptance_or_actuator_force',
    trial=name,input_sha256=digest.hexdigest(),original_packets=packets,start_ros_ns=start,end_ros_ns=end,
    sampled_rows=rows,statistics=statistics,nearest_native_packet=nearest,
    caveats=['raw collision sums keep original body-side force sign; support predicate remains FootContacts',
        'native command is pre-step; body references keep previous completed capture',
        'no assumed torque equality, no simulation replay or acceptance credit'])
(out/'result.json').write_text(json.dumps(value,indent=2,allow_nan=False))
print(json.dumps(dict(output=str(out),packets=packets,sampled=len(rows),statistics=statistics,
    force_command=[{k:j[k] for k in ('name','force_command','velocity','projected_transmitted_effort')}
                   for j in nearest['joints'] if j['name'].endswith('_calf_joint')])),flush=True)
