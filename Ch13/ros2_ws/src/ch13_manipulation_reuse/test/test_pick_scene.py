from pathlib import Path
import mujoco
import numpy as np
from ch13_manipulation_reuse.pick_scene import make_pick_model,contact_allowed
from ch13_navigation_reuse.scene import make_model

SOURCE=Path(__file__).resolve().parents[5].parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml'


def test_dynamic_body_appends_freejoint_without_altering_robot_or_caps():
    original=make_model(SOURCE,'vision');model=make_pick_model(SOURCE)
    assert (model.nq,model.nv,model.nu)==(34,32,19)
    assert model.neq==original.neq
    for name in ['base','link1','link2','link3','link4','link5','link6','link7','link8']:
        a,b=original.body(name).id,model.body(name).id
        np.testing.assert_array_equal(original.body_mass[a],model.body_mass[b])
        np.testing.assert_array_equal(original.body_inertia[a],model.body_inertia[b])
    np.testing.assert_array_equal(original.actuator_ctrlrange,model.actuator_ctrlrange)
    target=model.body('reuse_pick_target').id
    assert model.body_mass[target]==.02
    joint=model.body_jntadr[target];assert int(model.jnt_type[joint])==0
    assert model.jnt_qposadr[joint]==27
    data=mujoco.MjData(model);data.qpos[:]=model.key_qpos[model.key('home').id]
    np.testing.assert_allclose(data.qpos[27:30],[1.8,0.,.54])


def test_only_designated_finger_target_pairs_are_permitted_in_grasp_phase():
    assert contact_allowed('link7','reuse_pick_target','GRASP_APPROACH',True)
    assert contact_allowed('link8','reuse_pick_target','LIFT',True)
    assert not contact_allowed('link6','reuse_pick_target','LIFT',True)
    assert not contact_allowed('link7','reuse_pedestal','LIFT',True)
    assert not contact_allowed('link7','reuse_pick_target','PRE_GRASP',True)
    assert not contact_allowed('link7','reuse_pick_target','LIFT',False)
