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

@pytest.mark.parametrize('name',['level2_obstacles','level3_house'])
def test_survey_has_structural_footprint_clearance(monkeypatch,name):
    from ch13_navigation_reuse.scene import map_layout
    from ch13_navigation_reuse.map_target import occupancy_data
    from ch13_navigation_reuse.approach_geometry import footprint_clear
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1');monkeypatch.setenv('CH13_VALIDATION_SCENARIO',name)
    scenario=get_scenario(name);root=Path(__file__).resolve().parents[5]
    fp=json.loads((root/'Ch13/ros2_ws/src/ch13_navigation_reuse/config/footprint.json').read_text())['footprint']
    fp=[[x+math.copysign(.01,x),y+math.copysign(.01,y)] for x,y in fp]
    grid=dict(width=120,height=100,resolution=.05,origin=[-2.,-2.5],data=occupancy_data(map_layout('vision')))
    assert footprint_clear(scenario.survey_pose,grid,fp)
    assert get_scenario('level1_floor').pre_distance_m==.06


def test_house_fixture_uses_the_audited_west_approach_with_reverse_return():
    assert get_scenario('level3_house').approach_bearings==(0.,)
