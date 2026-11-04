import json
from pathlib import Path
from types import SimpleNamespace
import mujoco
import numpy as np
from ch13_navigation_reuse import approach_geometry
from ch13_manipulation_reuse.pick_monitor import PickMonitor
from ch13_manipulation_reuse.pick_scene import make_pick_model
from ch13_system_validation.transport import TransportLease
from ch13_system_validation.scenarios import get_scenario
from ch13_system_validation.physics import assess_transport


def test_floor_approach_can_select_the_verified_standoff_without_changing_default(monkeypatch):
    monkeypatch.setattr(approach_geometry,'arm_reach',lambda *args:.9)
    monkeypatch.setattr(approach_geometry,'position_ik',lambda *args:{'collision_free':True})
    monkeypatch.setattr(approach_geometry,'footprint_clear',lambda *args:True)
    q=np.zeros(27);q[3]=1.;fp=[[-.3,-.3],[.3,-.3],[.3,.3],[-.3,.3]]
    selected=approach_geometry.candidates(None,q,[2.,0.,.04],{},fp,distances=(.6,))
    assert len(selected)==3 and all(row['distance_from_observed_surface_m']==.6 for row in selected)
    assert len(approach_geometry.candidates(None,q,[2.,0.,.04],{},fp))==9


def model(monkeypatch):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1');monkeypatch.setenv('CH13_VALIDATION_SCENARIO','level1_floor')
    root=Path(__file__).resolve().parents[5]
    return make_pick_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml')


def test_floor_contact_is_measured_without_a_duplicate_receiving_body(monkeypatch):
    m=model(monkeypatch);d=mujoco.MjData(m);d.qpos[:]=m.key_qpos[m.key('home').id]
    d.qpos[29]=.0395;mujoco.mj_forward(m,d)
    monitor=PickMonitor(m);lease=TransportLease('test')
    monitor.step(SimpleNamespace(mjData=d,desired_joint_pos_gripper=.03),lease,1_000_000_000)
    assert monitor.support_N>.01
    assert not get_scenario('level1_floor').receiving_support_ready(monitor.support_N,{'point':[2.,0.,.04]})


def test_real_arm_body_penetration_latches_floor_fault_instead_of_becoming_carry_authority(monkeypatch):
    m=model(monkeypatch);d=mujoco.MjData(m);d.qpos[:]=m.key_qpos[m.key('home').id]
    fixture=json.loads((Path(__file__).parent/'data/floor_pose_candidates.json').read_text())
    d.qpos[0]=fixture['base_x'];d.qpos[2]=fixture['unsafe_base_z']
    d.qpos[19:25]=fixture['unsafe_pre'];d.qpos[25:27]=[.03,-.03];mujoco.mj_forward(m,d)
    lease=TransportLease('test');lease.phase='READY';lease.message={'task_phase':'PRE_GRASP'}
    monitor=PickMonitor(m);monitor.step(SimpleNamespace(mjData=d,desired_joint_pos_gripper=.03),lease,1_000_000_000)
    assert lease.phase=='FAULT' and lease.fault=='FLOOR_ARM_CONTACT'


def test_floor_physical_grading_requires_the_explicit_floor_receiver():
    rows=[]
    for index in range(101):
        carry=index<50
        rows.append(dict(sim_s=index*.1,phase='CARRY' if carry else 'RETREAT',
            target=[1.-index*.02,0.,.14] if carry else [-.6,0.,.04],relative_tcp=[0.,0.,0.],
            target_contact_N={'link7':.1,'link8':.1} if carry else {'link7':0.,'link8':0.},
            target_support_N=0. if carry else .19))
    assert assess_transport(rows,scenario=get_scenario('level1_floor'))['result']=='PASS'
    assert assess_transport(rows)['result']=='FAIL'
