"""Static camera projection only; this is not a physical placement verdict."""
import math
from pathlib import Path
import mujoco
import numpy as np
from ch13_manipulation_reuse.pick_scene import make_pick_model


def test_receiving_cylinder_stays_inside_original_camera_frustum(monkeypatch):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1')
    source=Path(__file__).resolve().parents[5].parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml'
    model=make_pick_model(source);data=mujoco.MjData(model)
    data.qpos[:]=model.key_qpos[model.key('home').id]
    data.qpos[:3]=[0.,0.,.30];data.qpos[3:7]=[0.,0.,0.,1.]
    mujoco.mj_forward(model,data)
    camera=model.camera('reuse_rgbd').id;support=model.geom('reuse_receiving_support').id
    center=model.geom_pos[support].copy();center[2]+=model.geom_size[support,2]+.04
    corners=np.array([center+[x*.02,y*.02,z*.04] for x in (-1,1) for y in (-1,1) for z in (-1,1)])
    optical=data.cam_xmat[camera].reshape(3,3)@np.diag([1.,-1.,-1.])
    points=(corners-data.cam_xpos[camera])@optical
    assert np.all(points[:,2]>.01)
    focal=240/(2*math.tan(math.radians(55)/2))
    pixels=points[:,:2]/points[:,2,None]*focal+[159.5,119.5]
    assert np.all((pixels[:,0]>1)&(pixels[:,0]<318)&(pixels[:,1]>1)&(pixels[:,1]<238)),pixels.tolist()
