import math
import json
import numpy as np
import mujoco
import pytest
from pathlib import Path
from scipy.spatial.transform import Rotation
from ch13_system_validation.scenarios import get_scenario


def test_level23_geometry_and_original_profiles_are_explicit():
    from ch13_system_validation.worlds import elements
    assert elements(get_scenario('development')) == ()
    assert elements(get_scenario('level1_floor')) == ()
    second = get_scenario('level2_obstacles')
    third = get_scenario('level3_house')
    assert second.target_xyz == (3., 1., .54)
    assert third.target_xyz == (3., 1., .04)
    assert second.survey_pose and third.survey_pose
    assert len(second.record()['world_geometry']) > 6
    assert len(third.record()['world_geometry']) > 6


def test_ramp_top_faces_are_five_degrees_and_join_without_a_step():
    from ch13_system_validation.worlds import elements
    ramps = [g for g in elements(get_scenario('level2_obstacles')) if g.terrain]
    assert len(ramps) == 2
    for geom, start, end in zip(ramps, (.45, .70), (.70, .95)):
        assert abs(geom.pitch_deg) == 5.
        assert not geom.navigation_obstacle
        rotation = Rotation.from_euler('y', geom.pitch_deg, degrees=True).as_matrix()
        top = np.array(geom.center) + rotation @ [0., 0., geom.half[2]]
        normal = rotation[:, 2]
        def height(x): return top[2] - normal[0] / normal[2] * (x - top[0])
        expected = .25 * math.tan(math.radians(5.))
        np.testing.assert_allclose([height(start), height(end)], [0., expected] if geom.pitch_deg < 0 else [expected, 0.], atol=1e-10)


def test_map_keeps_table_legs_and_door_but_not_table_top_or_walkable_ramp(monkeypatch):
    from ch13_navigation_reuse.scene import map_layout
    monkeypatch.setenv('CH13_VALIDATION_PROFILE', 'carry_v1')
    for name in ('level2_obstacles', 'level3_house'):
        monkeypatch.setenv('CH13_VALIDATION_SCENARIO', name)
        names = {g[0] for g in map_layout('vision')}
        assert 'table_top' not in names
        assert 'ramp_up' not in names and 'ramp_down' not in names
        assert all('table_leg_' + str(i) in names for i in range(4))
        assert ('door_lower' in names) == (name == 'level3_house')


def test_actual_models_preserve_actuators_and_put_target_under_house_table(monkeypatch):
    from ch13_manipulation_reuse.pick_scene import make_pick_model
    monkeypatch.setenv('CH13_VALIDATION_PROFILE', 'carry_v1')
    root = Path(__file__).resolve().parents[5]
    source = root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml'
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO', 'level1_floor')
    original = make_pick_model(source)
    for name in ('level2_obstacles', 'level3_house'):
        monkeypatch.setenv('CH13_VALIDATION_SCENARIO', name)
        model = make_pick_model(source)
        assert (model.nq, model.nv, model.nu) == (34, 32, 19)
        np.testing.assert_array_equal(model.actuator_trnid, original.actuator_trnid)
        np.testing.assert_array_equal(model.actuator_ctrlrange, original.actuator_ctrlrange)
        assert model.geom('reuse_table_top').size[2] == .035
        if name == 'level3_house':
            lower = model.geom('reuse_door_lower')
            upper = model.geom('reuse_door_upper')
            assert abs((upper.pos[1]-upper.size[1])-(lower.pos[1]+lower.size[1])-1.1) < 1e-10
            assert model.body('reuse_pick_target').pos[2] < model.geom('reuse_table_top').pos[2]-.035
        else:
            assert model.geom('reuse_ramp_up').group == 0


@pytest.mark.parametrize('name', ['level2_obstacles', 'level3_house'])
def test_level23_actual_camera_fits_target_at_survey_and_approach(monkeypatch,name):
    from ch13_manipulation_reuse.pick_scene import make_pick_model
    from ch13_manipulation_reuse.cylinder_vision import fit_cylinder
    from ch13_navigation_reuse.camera_worker import render_rgbd,camera_scene_option
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1')
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO',name)
    scenario=get_scenario(name)
    source=Path(__file__).resolve().parents[5].parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml'
    model=make_pick_model(source);model.vis.quality.offsamples=0
    data=mujoco.MjData(model);camera=model.camera('reuse_rgbd').id
    sx,sy,yaw=scenario.survey_pose
    approach=np.array(scenario.target_xyz[:2])-scenario.approach_standoff_m*np.array([math.cos(yaw),math.sin(yaw)])
    focal=240/(2*math.tan(math.radians(55)/2))
    with mujoco.Renderer(model,240,320) as renderer:
        for x,y in ((sx,sy),approach):
            data.qpos[:]=model.key_qpos[model.key('home').id]
            data.qpos[:2]=[x,y];data.qpos[3:7]=[math.cos(yaw/2),0.,0.,math.sin(yaw/2)]
            mujoco.mj_forward(model,data)
            renderer.update_scene(data,camera='reuse_rgbd',scene_option=camera_scene_option(True))
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=False
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SKYBOX]=False
            rgb,depth=render_rgbd(renderer,model,single_pass=True)
            transform=np.eye(4);transform[:3,:3]=data.cam_xmat[camera].reshape(3,3)@np.diag([1.,-1.,-1.])
            transform[:3,3]=data.cam_xpos[camera]
            fit=fit_cylinder(rgb,depth,[focal,focal,159.5,119.5],transform,.02,.08,robust_consensus=True)
            np.testing.assert_allclose(fit['center'],scenario.target_xyz,atol=.004)


def test_saved_house_approach_adds_valid_cardinal_candidates_without_bypassing_legs(monkeypatch):
    from ch13_navigation_reuse.scene import make_model,map_layout
    from ch13_navigation_reuse.approach_geometry import candidates
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1')
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO','level3_house')
    root=Path(__file__).resolve().parents[5]
    fixture=json.loads((Path(__file__).parent/'data/level3_survey_approach_v26.json').read_text())
    model=make_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml','vision')
    fp=json.loads((root/'Ch13/ros2_ws/src/ch13_navigation_reuse/config/footprint.json').read_text())['footprint']
    grid=dict(width=120,height=100,resolution=.05,origin=[-2.,-2.5],data=[])
    obstacles=map_layout('vision')
    for y in range(100):
        for x in range(120):
            px=-2+(x+.5)*.05;py=-2.5+(y+.5)*.05
            grid['data'].append(100 if any(abs(px-p[0])<=z[0]+.025 and abs(py-p[1])<=z[1]+.025 for _,p,z in obstacles) else 0)
    q=np.array(fixture['qpos']);point=fixture['point']
    assert candidates(model,q,point,grid,fp,distances=(.6,))==[]
    extra=candidates(model,q,point,grid,fp,distances=(.6,),bearings=(0.,math.pi/2,math.pi,3*math.pi/2))
    assert len(extra)==3 and all(r['ik']['collision_free'] for r in extra)
