"""Compare native dynamics with the independent energy/Jacobian derivative."""
import json
from pathlib import Path
import numpy as np
import pytest

def test_full_equilibrium_matches_independent_derivative():
    from integrated_robot_navigation.native_equilibrium import NativeEquilibrium
    f=json.loads((Path(__file__).parent/'fixtures/discrete_equilibrium_baseline.json').read_bytes())
    with NativeEquilibrium(f['urdf']) as core:
        result=core.evaluate(joints=f['joints'],body_pose=f['body_pose'],command_joints=f['command_joints'],forces=f['forces_world_flat'])
        expected=np.asarray(f['expected_force_derivative'])
        np.testing.assert_allclose(result['force_derivative'],expected,rtol=2e-7,atol=2e-5)
        assert result['mass_kg']==pytest.approx(15.2101,abs=1e-9)
        assert result['linear_residual']<1e-6
        assert result['wall_ns']<10_000_000
    with pytest.raises(RuntimeError,match='closed'):
        core.evaluate(joints=f['joints'],body_pose=f['body_pose'],command_joints=f['command_joints'],forces=f['forces_world_flat'])


def test_clipped_actuator_has_zero_command_sensitivity_and_boundary_is_rejected():
    from integrated_robot_navigation.native_equilibrium import NativeEquilibrium
    f=json.loads((Path(__file__).parent/'fixtures/discrete_equilibrium_baseline.json').read_bytes())
    name='fl_calf_joint';command=dict(f['command_joints'])
    with NativeEquilibrium(f['urdf']) as core:
        i=core.names.index(name);gain=core.plan['gains'][i];cap=core.plan['effort'][i]
        command[name]=f['joints'][name]-(cap+1.)/gain
        r=core.evaluate(joints=f['joints'],body_pose=f['body_pose'],command_joints=command,forces=f['forces_world_flat'])
        col=f['leg_names'].index(name)
        np.testing.assert_allclose(r['force_derivative'][:,col],0.,atol=1e-12)
        command[name]=f['joints'][name]-cap/gain
        with pytest.raises(ValueError,match='nondifferentiable actuator boundary'):
            core.evaluate(joints=f['joints'],body_pose=f['body_pose'],command_joints=command,forces=f['forces_world_flat'])
