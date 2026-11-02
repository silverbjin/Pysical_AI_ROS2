import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from independent_contact_model import build
repo=Path('/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2');n=repo/'Ch13/ros2_ws/src/integrated_robot_navigation';fixture=n/'test/fixtures/native_d504_infeasible.json';f=json.loads(fixture.read_bytes());m=build(f)
root=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b';dart=json.loads((root/'dart-static-mapping-7d150460-7eab-4ebd-a491-5dc92aa40dd4/evaluate.stdout').read_bytes())
expected={r['joint']:r['predicted_command_at_zero_velocity_nm'] for r in dart['rows']}
command=dict(zip(m['joint_names'],m['command'][6:].tolist()));error=max(abs(command[n]-v) for n,v in expected.items());assert error<1e-9,error
golden=dict(scope='independent full inertia/damping affine actuator map at original failed267 posture',names=m['joint_names'],gravity=m['gravity'][6:].tolist(),force_to_command=(-m['mapped'][6:]).tolist(),effort=m['effort'][6:].tolist(),expected_commands=command,dart_leg_command_max_error_nm=error,
 fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),independent_method_sha256=hashlib.sha256((Path(__file__).parent/'independent_contact_model.py').read_bytes()).hexdigest(),next_fr_tripod_minimax_expected=.8804416985839567)
(n/'test/fixtures/native_d504_discrete_command_terms.json').write_text(json.dumps(golden,indent=2))
(root/'task8-discrete-support-golden.method.py').write_bytes(Path(__file__).read_bytes())
(n/'test/test_discrete_support_actuation.py').write_text('''"""Actuation-aware support planning uses the independently checked DART map."""
import json
from pathlib import Path
import numpy as np
import pytest
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_equilibrium import NativeEquilibrium
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.contact_equilibrium import static_support

def inputs():
    folder=Path(__file__).parent/'fixtures'
    f=json.loads((folder/'native_d504_infeasible.json').read_bytes())
    golden=json.loads((folder/'native_d504_discrete_command_terms.json').read_bytes())
    return f,golden,compile_model(f['urdf'])

def test_native_affine_actuator_terms_match_independent_energy_and_DART_oracle():
    f,golden,model=inputs();a=f['args']
    with NativeEquilibrium(model.urdf) as core:
        result=core.contact_command_terms(model,a['joints'],a['body_pose'],a['points'])
        assert list(result['names'])==golden['names']
        for key in ('gravity','force_to_command','effort'):
            np.testing.assert_allclose(result[key],golden[key],atol=1e-9,rtol=1e-10)
        forces=np.array([a['forces_world'][foot] for foot in model.feet]).ravel()
        predicted=result['gravity']+result['force_to_command']@forces
        np.testing.assert_allclose(predicted,[golden['expected_commands'][name] for name in result['names']],atol=1e-9,rtol=0.)

def test_next_tripod_uses_actual20_axis_limits_without_raising_original_caps():
    f,golden,model=inputs();a=f['args'];active=tuple(foot for foot in model.feet if foot!=a['foot'])
    with NativeMassEvaluator(model) as mass,NativeEquilibrium(model.urdf) as core:
        com=mass(model,a['joints'],a['body_pose'])
        args=dict(model=model,joints=a['joints'],body_pose=a['body_pose'],points=a['points'],active_feet=active,com=com,terms_evaluator=mass.contact_terms)
        legacy=static_support(**args)
        result=static_support(**args,actuation_evaluator=core.contact_command_terms)
        assert legacy['torque_utilization']<.3
        assert result['feasible'] and result['actuation_model']=='gazebo_discrete_equilibrium_v1'
        assert result['torque_utilization']==pytest.approx(golden['next_fr_tripod_minimax_expected'],abs=2e-7)
        assert len(result['actuator_command_efforts'])==20
        assert all(abs(v)<=model.limits[name][3]+1e-7 for name,v in result['actuator_command_efforts'].items())
        assert all(abs(v)<=model.limits[name][3]+1e-7 for name,v in result['joint_torques'].items())
        force=np.array([result['forces_world'][foot] for foot in model.feet]);np.testing.assert_allclose(force.sum(axis=0),[0.,0.,15.2101*9.81],atol=1e-7)
        assert result['forces_world'][a['foot']]==[0.,0.,0.]
''')
print(json.dumps({'DART_leg_error_nm':error,'native_terms_method_not_yet_implemented':True}))
