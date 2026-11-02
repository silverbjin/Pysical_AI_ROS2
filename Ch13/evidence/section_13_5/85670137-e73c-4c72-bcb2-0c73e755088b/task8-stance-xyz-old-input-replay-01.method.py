"""Adapt an old height input to XYZ; never claim a recorded future swing."""
import hashlib,json,sys,time,copy
from pathlib import Path
import numpy as np
root=Path.cwd();src=root/'Ch13/ros2_ws/src/integrated_robot_navigation'
sys.path.insert(0,str(src))
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.leg_kinematics import fk_leg
from integrated_robot_navigation.load_xyz import SpatialXYZTransition
fixture=src/'test/fixtures/native_26a3_spatial_budget.json';data=json.loads(fixture.read_text())
model=compile_model(data['urdf']);args=copy.deepcopy(data['args']);pose=np.array(args['reference_pose'])
refs={f:(pose@np.r_[fk_leg(model,f,[args['command_joints'][f[:2]+'_'+p+'_joint'] for p in ('hip','thigh','calf')]),1.])[:3]
    for f in model.feet}
orig={f:v.copy() for f,v in refs.items()};height=args.pop('reference_z');old_orig=args.pop('origins')
for f in model.feet:refs[f][2]=height[f];orig[f][2]=old_orig[f]
args.update(reference_xyz=refs,origins=orig,future_targets=copy.deepcopy(refs))
def canonical(value):
    return json.loads(json.dumps(value,default=lambda v:v.tolist() if isinstance(v,np.ndarray) else v.item(),allow_nan=False))
report=dict(scope='adapted_old_input_arithmetic_not_actual_XYZ_or_engine',
    limitations=['future swing was not recorded: fixed current XY only','no simulated feedback or repeated integration'],
    fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
    method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (src/'integrated_robot_navigation').glob('*.py')},
    numeric_input=canonical(args),attempts=[])
with NativeMassEvaluator(model) as core:
    report['native_provenance']=core.provenance
    kernel=SpatialXYZTransition(model,default_limits(),terms_evaluator=core.contact_terms);kernel.prepare()
    for index in range(24):
        attempt=dict(index=index)
        try:attempt['delta']=kernel.step(**args);attempt['model']=kernel.last_model
        except ValueError as error:attempt['error']=str(error)
        attempt['trace']=kernel.last_attempt;report['attempts'].append(attempt)
report['failed']=sum('error' in a for a in report['attempts'])
out=Path(sys.argv[1]);assert not out.exists();out.write_text(json.dumps(report,indent=2))
method=out.with_suffix('.method.py');assert not method.exists();method.write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(out),failed=report['failed'],
    wall_ns=[a['trace']['stages'].get('exact_ik_validated',{}) .get('wall_ns') for a in report['attempts']])))
raise SystemExit(1 if report['failed'] else 0)
