"""Reuse one existing native full-contact edge, avoiding a new diagnostic run."""
import json,hashlib,uuid
from pathlib import Path
base=Path.cwd()/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
name='native-g2-gazebo-c6ee257f-512c-487b-9a1f-1f2be2ac05e1';copy=base/name
t=json.loads((copy/'teardown.json').read_text());assert t['parent_reaped'] and not t['residual_live_pids']
source=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/name/'native_controls.json'
records=json.loads(source.read_text())['records'];selected=None
for record in reversed(records):
    for body in reversed(record['body_references']):
        if body.get('contact_event_joints') and body['raw_contacts']['details_included']:
            selected=body;break
    if selected is not None:break
assert selected is not None
joints={j['name']:j for j in selected['contact_event_joints']['joints']};rows=[]
for foot in selected['raw_contacts']['feet']:
    total=[0.,0.,0.]
    for pair in foot['pairs']:
        if pair['collision1_id']==foot['entity']:forces=pair['force1_world']
        elif pair['collision2_id']==foot['entity']:forces=pair['force2_world']
        else:raise ValueError('raw foot collision identity mismatch')
        for f in forces:total=[a+b for a,b in zip(total,f)]
    calf=joints[foot['name'][:2]+'_calf_joint']
    rows.append(dict(foot=foot['name'],measured_ground_force_world_n=total,
        calf_force_command=calf['force_command'],calf_projected_transmitted_effort=calf['projected_transmitted_effort'],
        calf_position_reference=calf.get('position_reference')))
out=base/('full-contact-discriminator-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
(out/'original-event.json').write_text(json.dumps(selected,indent=2,allow_nan=False))
v=dict(scope='actual_native_contact_edge_not_final_fault',trial=name,
    capture_ns=selected['capture_ns'],input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),rows=rows,
    caveats=['earlier contact edge differs from final fault','force_command is an intent, transmitted effort is not automatically actuator torque'])
(out/'result.json').write_text(json.dumps(v,indent=2,allow_nan=False));print(json.dumps(dict(output=str(out),**v)),flush=True)
