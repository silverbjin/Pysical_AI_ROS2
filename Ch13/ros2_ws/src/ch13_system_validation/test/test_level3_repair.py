"""Saved actual states pin a physically checked pre-grasp, not position-only IK."""
import json,math
from pathlib import Path
import mujoco,numpy as np,pytest
from scipy.spatial.transform import Rotation
from ch13_system_validation.scenarios import get_scenario,grasp_pose
from ch13_manipulation_reuse.pick_scene import make_pick_model
from ch13_manipulation_reuse.model import TCP_LINK6

FIXTURES=json.loads((Path(__file__).parent/'data/level3_collision_free_pregrasp.json').read_text())

@pytest.mark.parametrize('row',FIXTURES,ids=lambda r:r['uuid'][:8])
def test_saved_actual_level3_pregrasp_matches_collision_free_full_pose(monkeypatch,row):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1')
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO','level3_house')
    root=Path(__file__).resolve().parents[5]
    model=make_pick_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml')
    data=mujoco.MjData(model);data.qpos[:]=row['qpos']
    for i,value in enumerate(row['q_arm'],1):data.qpos[model.jnt_qposadr[model.joint('joint'+str(i)).id]]=value
    mujoco.mj_forward(model,data)
    center=np.array(row['center']);forward=center-np.array([*data.qpos[:2],center[2]])
    expected,rotation=grasp_pose(center,forward,-1.,get_scenario('level3_house'))
    link=model.body('link6').id;actual_rotation=data.xmat[link].reshape(3,3)
    actual=data.xpos[link]+actual_rotation@TCP_LINK6
    assert np.linalg.norm(actual-expected)<.001
    assert (Rotation.from_matrix(actual_rotation).inv()*rotation).magnitude()<.01
    for contact in data.contact:
        a,b=map(int,contact.geom);an=model.body(model.geom_bodyid[a]).name;bn=model.body(model.geom_bodyid[b]).name
        if an.startswith('link') or bn.startswith('link'):
            assert contact.dist>=-.0001 or {an,bn}<={'link7','link8'},(an,bn,contact.dist)

def test_house_survey_enters_final_approach_along_same_heading():
    scenario=get_scenario('level3_house');x,y,yaw=scenario.survey_pose
    # Avoid an additional final yaw turn alongside the legs; no yaw permission change.
    assert abs(y-scenario.target_xyz[1])<.01
    assert abs(yaw)<.01 and x<scenario.target_xyz[0]-scenario.approach_standoff_m-.3
    assert get_scenario('level1_floor').pre_distance_m==.06
