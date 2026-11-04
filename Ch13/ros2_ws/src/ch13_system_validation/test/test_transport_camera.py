"""Frozen post-exit states test visibility; no stepping or live robot authority."""
import json,math
from pathlib import Path
import mujoco
import numpy as np
import pytest
from ch13_manipulation_reuse.pick_scene import make_pick_model
from ch13_manipulation_reuse.cylinder_vision import fit_cylinder
from ch13_navigation_reuse.camera_worker import render_rgbd


@pytest.mark.parametrize('fixture',['held_visibility_v5.json','camera_trace_v5_v8_dense.json'])
def test_transport_camera_keeps_original_fit_visible_in_saved_pick_and_carry_states(monkeypatch,fixture):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1')
    source=Path(__file__).resolve().parents[5].parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml'
    model=make_pick_model(source);model.vis.quality.offsamples=0
    data=mujoco.MjData(model);camera=model.camera('reuse_rgbd').id
    option=mujoco.MjvOption();option.geomgroup[2]=0;option.geomgroup[3]=1;option.geomgroup[5]=1
    states=json.loads((Path(__file__).parent/'data'/fixture).read_text())['states']
    focal=240/(2*math.tan(math.radians(55)/2));renderer=mujoco.Renderer(model,240,320)
    try:
        for state in states:
            data.qpos[:]=state['qpos'];mujoco.mj_forward(model,data)
            renderer.update_scene(data,camera='reuse_rgbd',scene_option=option)
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=False
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SKYBOX]=False
            rgb,depth=render_rgbd(renderer,model,single_pass=True)
            transform=np.eye(4);transform[:3,:3]=data.cam_xmat[camera].reshape(3,3)@np.diag([1.,-1.,-1.]);transform[:3,3]=data.cam_xpos[camera]
            fit=fit_cylinder(rgb,depth,[focal,focal,159.5,119.5],transform,.02,.08,robust_consensus=True)
            # Ground truth is an assertion after fitting, never an estimator input.
            np.testing.assert_allclose(fit['center'],state['qpos'][27:30],atol=.004,err_msg=str(state['sim_s']))
    finally:renderer.close()


def test_legacy_camera_extrinsics_are_preserved_without_transport_profile(monkeypatch):
    monkeypatch.delenv('CH13_VALIDATION_PROFILE',raising=False)
    source=Path(__file__).resolve().parents[5].parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml'
    model=make_pick_model(source)
    np.testing.assert_array_equal(model.cam_pos[model.camera('reuse_rgbd').id],[.4,.25,.25])


def test_floor_camera_observes_initial_and_verified_full_pose_endpoints(monkeypatch):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1')
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO','level1_floor')
    source=Path(__file__).resolve().parents[5].parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml'
    model=make_pick_model(source);model.vis.quality.offsamples=0;data=mujoco.MjData(model)
    fixture=json.loads((Path(__file__).parent/'data/floor_pose_candidates.json').read_text())
    initial=model.key_qpos[model.key('home').id].copy();camera=model.camera('reuse_rgbd').id
    option=mujoco.MjvOption();option.geomgroup[2]=0;option.geomgroup[3]=1;option.geomgroup[5]=1
    focal=240/(2*math.tan(math.radians(55)/2))
    with mujoco.Renderer(model,240,320) as renderer:
        for state in ('initial','safe_pre','safe_grasp'):
            data.qpos[:]=initial
            if state!='initial':
                data.qpos[0]=fixture['base_x'];data.qpos[2]=fixture['safe_base_z']
                data.qpos[19:25]=fixture[state]
                opening=.03 if state=='safe_pre' else .019739593607788333
                data.qpos[25:27]=[opening,-opening]
            mujoco.mj_forward(model,data);renderer.update_scene(data,camera='reuse_rgbd',scene_option=option)
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=False
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SKYBOX]=False
            rgb,depth=render_rgbd(renderer,model,single_pass=True)
            transform=np.eye(4);transform[:3,:3]=data.cam_xmat[camera].reshape(3,3)@np.diag([1.,-1.,-1.]);transform[:3,3]=data.cam_xpos[camera]
            fit=fit_cylinder(rgb,depth,[focal,focal,159.5,119.5],transform,.02,.08,robust_consensus=True)
            np.testing.assert_allclose(fit['center'],fixture['target'],atol=.002,err_msg=state)
