"""Book floor scenario is explicit and cannot masquerade as the development rig."""
from dataclasses import FrozenInstanceError
from pathlib import Path
import numpy as np
import pytest
import mujoco
from ch13_system_validation.scenarios import get_scenario,active_scenario,grasp_pose,retreat_point


def test_development_defaults_are_immutable_and_unknown_scenario_is_rejected(monkeypatch):
    monkeypatch.delenv('CH13_VALIDATION_SCENARIO',raising=False)
    scenario=active_scenario()
    assert scenario.name=='development' and scenario.target_xyz==(1.8,0.,.54)
    assert scenario.receiving_xyz==(-.8,0.,.54) and scenario.pre_distance_m==.12
    with pytest.raises(FrozenInstanceError):scenario.name='level1_floor'
    with pytest.raises(ValueError):get_scenario('unknown')


def test_floor_geometry_uses_inclined_short_approach_without_changing_legacy():
    center=np.array([2.,0.,.04]);forward=np.array([1.,0.,0.])
    pre,rotation=grasp_pose(center,forward,-1.,get_scenario('level1_floor'))
    np.testing.assert_allclose(np.linalg.norm(center-pre),.06)
    assert rotation.as_matrix()[2,2]==pytest.approx(-.5)
    assert pre[2]>.04
    old_pre,old_rotation=grasp_pose(center,forward,-1.,get_scenario('development'))
    np.testing.assert_allclose(old_pre,center-[.12,0.,0.])
    np.testing.assert_allclose(old_rotation.as_matrix()[:,2],forward)


def test_floor_release_needs_actual_support_and_observed_receiving_region():
    floor=get_scenario('level1_floor')
    assert floor.receiving_support_ready(.19,{'point':[-.6,0.,.04]})
    for force,point in ((0.,[-.6,0.,.04]),(.19,[2.,0.,.04]),(.19,[float('nan'),0.,.04])):
        assert not floor.receiving_support_ready(force,{'point':point})
    assert not floor.receiving_support_ready(.19,None)


def test_floor_retreat_reverses_the_approach_and_rises_while_legacy_stays_horizontal():
    floor=get_scenario('level1_floor');_,rotation=grasp_pose([-.6,0.,.04],[-1.,0.,0.],-1.,floor)
    tcp=np.eye(4);tcp[:3,:3]=rotation.as_matrix();tcp[:3,3]=[-.6,0.,.04]
    back=retreat_point(tcp,floor)
    assert back[0]>-.6 and back[2]>.04
    assert np.linalg.norm(back-tcp[:3,3])==pytest.approx(.08)
    np.testing.assert_allclose(retreat_point(tcp,get_scenario('development')),[-.52,0.,.04])


def test_floor_model_uses_original_ground_and_robot_with_no_fake_receiving_patch(monkeypatch):
    from ch13_manipulation_reuse.pick_scene import make_pick_model
    root=Path(__file__).resolve().parents[5]
    source=root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml'
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1')
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO','development');legacy=make_pick_model(source)
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO','level1_floor');floor=make_pick_model(source)
    np.testing.assert_allclose(floor.key_qpos[floor.key('home').id,27:30],[2.,0.,.04])
    assert mujoco.mj_name2id(floor,mujoco.mjtObj.mjOBJ_GEOM,'reuse_pedestal')==-1
    assert mujoco.mj_name2id(floor,mujoco.mjtObj.mjOBJ_GEOM,'reuse_receiving_support')==-1
    assert floor.geom('floor').id>=0
    for body in range(1,legacy.nbody):
        name=legacy.body(body).name
        if name=='reuse_pick_target':continue
        np.testing.assert_array_equal(floor.body_mass[floor.body(name).id],legacy.body_mass[body])
    np.testing.assert_array_equal(floor.actuator_ctrlrange,legacy.actuator_ctrlrange)
    assert floor.opt.timestep==legacy.opt.timestep==.002

@pytest.mark.parametrize('name,flag,expected',[('level3_house','0','baseline_navfn'),('level2_obstacles','1','experimental_se2'),('development','1','baseline_navfn')])
def test_record_freezes_the_navigation_profile_in_scenario_hash(monkeypatch,name,flag,expected):
    monkeypatch.setenv('CH13_EXPERIMENTAL_SE2',flag)
    assert get_scenario(name).record()['navigation_profile']==expected
