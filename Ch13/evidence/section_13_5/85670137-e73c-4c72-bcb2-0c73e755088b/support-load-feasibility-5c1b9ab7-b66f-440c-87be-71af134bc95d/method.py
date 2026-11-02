"""Closed-state bounded geometry discriminator, not a physics success."""
from pathlib import Path
import hashlib,json,uuid
import numpy as np
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.support import center_of_mass,support_margin
from integrated_robot_navigation.projection import body_rotation

base=Path.cwd()/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial=base/'native-g2-gazebo-15382b7e-0d5f-45dd-95f3-6500573a3f60'
closed=json.loads((trial/'teardown.json').read_text());assert closed['parent_reaped'] and not closed['residual_live_pids']
report=json.loads((trial/'controller_report.json').read_text());fault=report['first_fault']
run=json.loads((trial/'result.json').read_text());model=compile_model(Path(run['scene']['robot']['path']).read_text())
q=fault['samples']['joints']['data']['position'];body=fault['samples']['body']['data']
pose=np.eye(4);pose[:3,:3]=body_rotation(body)[0];pose[:3,3]=body['position']
com=np.asarray(center_of_mass(model,q,pose));reference=np.array(fault['reference_body'])
m=CrawlMachine(model,default_limits());m.state='CRAWL';m._targets={f:np.array(p) for f,p in fault['targets'].items()}
contact=fault['samples']['contacts']['data'];points=dict(zip(contact['names'],contact['points']))
selected=fault['state_before']['swing_foot'];support=[points[f] for f in model.feet if f!=selected]
matrix=np.vstack((np.array(support)[:,:2].T,np.ones(3)))
direction=np.mean(support,axis=0)[:2]-com[:2]
command=dict(q);command.update(m._solve(q,True,reference));baseline=np.asarray(center_of_mass(model,command,reference))
rows=[]
for weight in np.linspace(0.,1.,17):
    proposed=reference.copy();proposed[:2,3]+=direction*weight
    row=dict(weight=float(weight),body_delta_m=(direction*weight).tolist())
    try:
        values=dict(q);values.update(m._solve(q,True,proposed))
        predicted=com+center_of_mass(model,values,proposed)-baseline
        fractions=np.linalg.solve(matrix,np.r_[predicted[:2],1.])
        row.update(valid=True,predicted_com=predicted.tolist(),normal_load_fractions=fractions.tolist(),
            max_load_fraction=float(fractions.max()),margin_m=support_margin(predicted,support))
    except ValueError as e:row.update(valid=False,reason=str(e))
    rows.append(row)
valid=[r for r in rows if r['valid'] and r['margin_m']>=.025]
out=base/('support-load-feasibility-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
value=dict(scope='offline_fixed_pose_URDF_IK_and_quasistatic_vertical_load_prediction_not_native_success',
    trial=trial.name,input_sha256=hashlib.sha256((trial/'controller_report.json').read_bytes()).hexdigest(),
    measured_com=com.tolist(),support=support,selected=selected,rows=rows,
    best=min(valid,key=lambda r:r['max_load_fraction']) if valid else None,
    caveats=['ignores tangential force, saturation, dynamic response and touchdown',
        'valid means unchanged joint/footprint/thigh-collision bounds only; no controller command executed'])
(out/'result.json').write_text(json.dumps(value,indent=2,allow_nan=False))
print(json.dumps(dict(output=str(out),measured_com=value['measured_com'],baseline=rows[0],best=value['best'],
    invalid=[r for r in rows if not r['valid']])),flush=True)
