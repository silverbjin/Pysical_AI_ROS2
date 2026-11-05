"""A map update is geometry, never permission to move or fabricated perception."""
import copy,json
from types import SimpleNamespace
import pytest
from ch13_navigation_reuse.map_target import TargetMapGate,occupancy_data,attestation_matches,target_cell_clear

def status():
    return dict(session='episode',phase='CARRY_ARMED',task_phase='CARRY_ARMED',fault='',
        goal_id='outbound',transport_goal_id='reserved',transport_stage='ARMED',sequence=7,
        stamp_ns=1_000_000_000,capture_health_ns=990_000_000,decision_wall=10.,
        gripper_target_contacts={'link7':.1,'link8':.1},gripper_force_hold={'ready':True})

def bound():
    gate=TargetMapGate();initial=status();initial.update(phase='WAITING',task_phase='WAITING',sequence=0)
    assert not gate.observe(initial,'engine',10.01)
    return gate

def test_only_fresh_native_reserved_physical_hold_removes_old_target_once():
    gate=bound();row=status()
    assert gate.observe(row,'engine',10.02)
    assert gate.removed and gate.event['stamp_ns']==row['stamp_ns']
    assert gate.event['decision_wall']==10. and gate.event['source_gid']=='engine'
    assert not gate.observe(row,'engine',10.03)
    payload=gate.snapshot()
    assert attestation_matches(payload,'episode','outbound','reserved',10.04)
    for fields in [('other','outbound','reserved'),('episode','other','reserved'),('episode','outbound','other')]:
        assert not attestation_matches(payload,*fields,10.04)
    assert not attestation_matches(payload,'episode','outbound','reserved',10.5)

@pytest.mark.parametrize('change',[
    {'decision_wall':9.5},{'decision_wall':10.2},{'phase':'READY'},
    {'fault':'OBSERVATION_EXPIRED'},{'transport_stage':'PICK'},{'task_phase':'HOLD'},
    {'gripper_target_contacts':{'link7':.1,'link8':0.}},
    {'gripper_target_contacts':{'link7':float('nan'),'link8':.1}},
    {'gripper_force_hold':{'ready':False}},{'capture_health_ns':500_000_000},
    {'transport_goal_id':None},{'goal_id':None},{'sequence':0}])
def test_stale_incomplete_or_unheld_status_never_clears_map(change):
    gate=bound();row=status();row.update(change)
    assert not gate.observe(row,'engine',10.02)
    assert not gate.removed

@pytest.mark.parametrize('owner,session',[('replacement','episode'),('engine','replacement')])
def test_source_or_episode_replacement_latches_fault(owner,session):
    gate=bound();row=status();row['session']=session
    assert not gate.observe(row,owner,10.02)
    assert gate.fault and not gate.observe(status(),'engine',10.03)

def test_removing_target_preserves_overlapping_structural_occupancy():
    objects=[('target',[.5,.5,0],[.1,.1,.1]),('leg',[.6,.5,0],[.1,.1,.1])]
    initial=occupancy_data(objects,10,10,.1,[0,0])
    picked=occupancy_data([g for g in objects if g[0]!='target'],10,10,.1,[0,0])
    assert sum(picked)<sum(initial)
    assert picked[5*10+6]==100 and initial[5*10+6]==100

def test_costmap_update_requires_expected_frame_bounds_and_nonlethal_target_cell():
    meta=SimpleNamespace(resolution=.1,size_x=10,size_y=10,
        origin=SimpleNamespace(position=SimpleNamespace(x=0.,y=0.)))
    m=SimpleNamespace(header=SimpleNamespace(frame_id='reuse/map'),metadata=meta,data=[0]*100)
    assert target_cell_clear(m,[.5,.5])
    m.data[55]=253;assert target_cell_clear(m,[.5,.5])  # Inflation near table legs is not the removed object.
    for value in (254,255):
        m.data[55]=value;assert not target_cell_clear(m,[.5,.5])
    assert not target_cell_clear(m,[-1.,.5])
    m.header.frame_id='wrong';assert not target_cell_clear(m,[.2,.2])

def test_world_map_publishes_only_target_removal_after_native_hold(monkeypatch):
    import time,rclpy
    from std_msgs.msg import String
    from std_srvs.srv import Trigger
    from ch13_navigation_reuse.world_map import WorldMap
    from ch13_navigation_reuse.scene import map_layout
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1')
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO','level3_house')
    rclpy.init(domain_id=138);node=None
    try:
        node=WorldMap('vision');initial=list(node.map.data)
        row=status();row['decision_wall']=time.monotonic()
        node.status_message(String(data=json.dumps(row)),SimpleNamespace(publisher_gid=b'engine'))
        assert node.map_gate.removed
        expected=occupancy_data([g for g in map_layout('vision') if g[0]!='target'])
        assert list(node.map.data)==expected and list(node.map.data)!=initial
        response=node.target_state(None,Trigger.Response())
        assert response.success and json.loads(response.message)['event']['transport_goal_id']=='reserved'
    finally:
        if node is not None:node.destroy_node()
        rclpy.try_shutdown()

def test_legacy_map_has_no_moving_target_lifecycle(monkeypatch):
    import rclpy
    from ch13_navigation_reuse.world_map import WorldMap
    monkeypatch.delenv('CH13_VALIDATION_PROFILE',raising=False)
    rclpy.init(domain_id=138);node=None
    try:
        node=WorldMap('vision');assert node.map_gate is None
    finally:
        if node is not None:node.destroy_node()
        rclpy.try_shutdown()

@pytest.mark.parametrize('foreign',[False,True])
def test_worker_waits_for_matching_attestation_and_actual_costmap_without_nested_spin(monkeypatch,foreign):
    from ch13_system_validation import continuation
    clock=[10.02];depth=[0];closed=[];requests=[];records=[]
    def now():clock[0]+=.005;return clock[0]
    monkeypatch.setattr(continuation.time,'monotonic',now)
    gate=bound();assert gate.observe(status(),'engine',10.02)
    def reply(name):
        requests.append(name)
        if name.endswith('target_state'):
            value=gate.snapshot();value['last_receipt_wall']=now()
            if foreign:value['event']['transport_goal_id']='foreign'
            return SimpleNamespace(success=True,message=json.dumps(value))
        m=SimpleNamespace(header=SimpleNamespace(frame_id='reuse/map'),metadata=SimpleNamespace(
            resolution=.1,size_x=10,size_y=10,origin=SimpleNamespace(position=SimpleNamespace(x=0.,y=0.)),
            update_time=SimpleNamespace(sec=1,nanosec=0)),data=[0]*100)
        return SimpleNamespace(map=m)
    class Client:
        def __init__(self,name):self.name=name
        def service_is_ready(self):return True
        def call_async(self,req):
            value=reply(self.name)
            return SimpleNamespace(done=lambda:True,result=lambda:value)
    node=SimpleNamespace(create_client=lambda typ,name:Client(name),destroy_client=lambda client:closed.append(client.name))
    def until(predicate,seconds):
        depth[0]+=1;assert depth[0]==1
        try:
            for _ in range(60):
                if predicate():return True
            return False
        finally:depth[0]-=1
    args=dict(node=node,until=until,session='episode',goal='outbound',transport_goal='reserved',target=[.5,.5],records=records)
    if foreign:
        with pytest.raises(AssertionError):continuation.await_target_map(**args)
        assert not records
    else:
        continuation.await_target_map(**args)
        assert requests[-1]=='/global_costmap/get_costmap' and records[-1]['event']=='nav_target_map_cleared'
    assert len(closed)==2 and depth[0]==0
