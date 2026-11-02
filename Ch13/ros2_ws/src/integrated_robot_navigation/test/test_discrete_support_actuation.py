"""Actuation-aware support planning uses the independently checked DART map."""
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
