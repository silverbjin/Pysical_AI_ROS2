from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pytest
from ch13_sim_core.mujoco_runtime import MujocoRuntime

def test_reset_has_no_deep_initial_penetration():
    with MujocoRuntime() as r:
        # A narrow engine characterization check: initial impulses invalidate fixture alignment.
        assert all(c.dist > -.001 for c in r._data.contact)

def test_snapshot_reports_measured_body_velocity_not_synthetic_zero():
    import mujoco
    with MujocoRuntime() as r:
        j=mujoco.mj_name2id(r._model,mujoco.mjtObj.mjOBJ_JOINT,'base_free')
        start=r._model.jnt_dofadr[j]
        r._data.qvel[start:start+6]=[.1,.2,.3,.01,.02,.03]
        mujoco.mj_forward(r._model,r._data)
        s=r.snapshot()
        np.testing.assert_allclose(s.base_linear_velocity,[.1,.2,.3],atol=1e-8)
        np.testing.assert_allclose(s.base_angular_velocity,[.01,.02,.03],atol=1e-8)

def test_hold_and_small_arm_motion_are_finite_and_stable():
    with MujocoRuntime() as r:
        r.reset(seed=42)
        q=r.contract.nominal
        for _ in range(2000):
            r.step(1)
        q[12]=.08
        r.apply_named_targets(r.contract.names,q,r.snapshot().time)
        r.step(1000)
        s=r.snapshot()
        assert np.isfinite(s.positions).all()
        assert .38 < s.base_position[2] < .55
        assert s.base_tilt < .15
        assert s.positions[12] > .04

def test_snapshot_is_copy_and_stale_commands_rejected():
    r=MujocoRuntime()
    r.step(200)
    s=r.snapshot()
    s.positions[:]=99
    assert (r.snapshot().positions < 4.1).all()
    with pytest.raises(ValueError): r.apply_named_targets(r.contract.names,r.contract.nominal,0)
    r.close(); r.close()

def test_permuted_actuators_and_input_joints_map_by_name(tmp_path):
    from importlib.resources import files
    tree=ET.parse(str(files('ch13_sim_core').joinpath('models/integrated_robot.xml')))
    actuators=tree.find('actuator')
    actuators[:]=list(actuators)[::-1]
    p=tmp_path/'permuted.xml'; tree.write(p)
    with MujocoRuntime(p) as r:
        q=r.contract.nominal
        q[12]=.13
        r.apply_named_targets(r.contract.names[::-1],q[::-1],0.)
        r.step(500)
        assert r.snapshot().positions[12] > .09
