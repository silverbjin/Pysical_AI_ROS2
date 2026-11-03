from pathlib import Path
import numpy as np
import mujoco
from ch13_navigation_reuse.camera_worker import render_rgbd
from ch13_manipulation_reuse.pick_scene import make_pick_model


def test_one_actual_frame_preserves_rgb_and_native_metric_depth():
    root=Path(__file__).resolve().parents[5]
    model=make_pick_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml')
    model.vis.quality.offsamples=0;data=mujoco.MjData(model)
    data.qpos[:]=model.key_qpos[model.key('home').id];mujoco.mj_forward(model,data)
    option=mujoco.MjvOption();option.geomgroup[2]=0;option.geomgroup[3]=1;option.geomgroup[5]=1
    with mujoco.Renderer(model,height=240,width=320) as renderer:
        renderer.update_scene(data,camera='reuse_rgbd',scene_option=option)
        renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=False
        _,original_native_depth=render_rgbd(renderer,model,single_pass=False)
        renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SKYBOX]=False
        old_rgb,old_depth=render_rgbd(renderer,model,single_pass=False)
        rgb,depth=render_rgbd(renderer,model,single_pass=True)
    np.testing.assert_array_equal(rgb,old_rgb)
    mask=(rgb[:,:,0]>80)&(rgb[:,:,0]>1.8*rgb[:,:,1])&(rgb[:,:,0]>1.8*rgb[:,:,2])
    assert mask.sum()>=20
    np.testing.assert_allclose(depth[mask],old_depth[mask],atol=3e-6,rtol=0.)
    np.testing.assert_allclose(depth,old_depth,atol=1e-4,rtol=1e-4)
    np.testing.assert_allclose(depth,original_native_depth,atol=1e-4,rtol=1e-4)
    assert depth.shape==(240,320) and depth.dtype==np.float32
