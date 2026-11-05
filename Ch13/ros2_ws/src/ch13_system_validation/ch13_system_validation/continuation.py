"""Same-owner continuation of the live pick, never a new robot process."""
import math
import uuid
import time
import json
import numpy as np
from scipy.spatial.transform import Rotation
from unique_identifier_msgs.msg import UUID
from nav2_msgs.action import NavigateToPose
from nav2_msgs.srv import GetCostmap
from std_srvs.srv import Trigger
from rclpy.action import ActionClient
from ch13_navigation_reuse.command_gateway import set_stamp
from ch13_manipulation_reuse.planning import pose
from ch13_mission_orchestration.session import admit_observation
from .scene_contact import receiving_contact
from .transport import fresh_return_capture
from .scenarios import active_scenario,retreat_point
from .placed_scene import detach_released_cylinder
from .place_settling import PlacementSupportGate
from ch13_navigation_reuse.command_gateway import N
from ch13_navigation_reuse.map_target import attestation_matches,target_cell_clear


def make_navigation_goal(target,stamp_ns):
    goal=NavigateToPose.Goal();goal.pose.header.frame_id='reuse/map'
    set_stamp(goal.pose.header.stamp,stamp_ns)
    goal.pose.pose.position.x=float(target[0]);goal.pose.pose.position.y=float(target[1])
    goal.pose.pose.position.z=0.
    q=goal.pose.pose.orientation
    q.x=0.;q.y=0.;q.z=math.sin(target[2]/2);q.w=math.cos(target[2]/2)
    return goal


def drain_owned_goals(session,until,extra=()):
    tracker=session.goals;tracker.cancel()
    def drained():
        tracker.poll()
        return (tracker.drained and all(f.done() for f in extra)
            and all(r.get('cancel') is None or r['cancel'].done() for r in tracker.rows))
    assert until(drained,5.),'owned action send/result/cancel ACK drain deadline'
    assert not tracker.errors,tracker.errors


def await_target_map(*,node,until,session,goal,transport_goal,target,records):
    """Read-only geometry acknowledgement; all action authority stays native."""
    clients=[]
    try:
        for typ,name in ((Trigger,N+'/map/target_state'),(GetCostmap,'/global_costmap/get_costmap')):
            clients.append(node.create_client(typ,name))
        assert until(lambda:all(c.service_is_ready() for c in clients),3.),'target map services unavailable'
        phase=0;future=None;next_request=0.;attestation=None;costmap=None
        def updated():
            nonlocal phase,future,next_request,attestation,costmap
            now=time.monotonic()
            if future is None:
                if now<next_request:return False
                request=Trigger.Request() if phase==0 else GetCostmap.Request()
                future=clients[phase].call_async(request)
            if not future.done():return False
            response=future.result();future=None;now=time.monotonic();next_request=now+.05
            if phase==0:
                try:value=json.loads(response.message)
                except (TypeError,ValueError):return False
                if response.success and attestation_matches(value,session,goal,transport_goal,now):
                    attestation=value;phase=1
                return False
            costmap=response.map
            return target_cell_clear(costmap,target)
        assert until(updated,3.),'matching physical hold / global costmap target update absent'
        records.append(dict(event='nav_target_map_cleared',map_attestation=attestation,
            costmap_update_time=dict(sec=costmap.metadata.update_time.sec,nanosec=costmap.metadata.update_time.nanosec)))
    finally:
        for client in clients:node.destroy_client(client)


def continue_mission(*,session,call,node,until,snapshot,status,control,planner,grip,baseline_z,records,action_client_factory=ActionClient):
    scenario=active_scenario()
    session.port.complete('pick',dict(session=session.session))
    session.await_step('return',until)
    identity=uuid.uuid4();home=[0.,0.,math.pi]
    control['reserve_transport'](identity.hex,home);control['set_phase']('CARRY_ARMED')
    assert until(lambda:status().get('phase') in ('CARRY_ARMED','FAULT'),3.)
    assert status()['phase']=='CARRY_ARMED',status()
    if scenario.world in ('obstacles','house'):
        native=status()
        await_target_map(node=node,until=until,session=native['session'],goal=native['goal_id'],
                         transport_goal=identity.hex,target=scenario.target_xyz[:2],records=records)
    client=action_client_factory(node,NavigateToPose,'/navigate_to_pose');handle=None;result=None
    try:
        assert until(client.server_is_ready,3.)
        assert until(lambda:fresh_return_capture(snapshot()['boundary'],time.monotonic()),5.),'fresh original capture headroom before return missing'
        response=call('navigation/require_vision');assert response.success,response.message
        control['set_phase']('CARRY')
        response=call('navigation/enable');assert response.success,response.message
        goal=make_navigation_goal(home,snapshot()['clock_ns'])
        sent=client.send_goal_async(goal,goal_uuid=UUID(uuid=list(identity.bytes)))
        if not getattr(client,'tracked_by_session',False):session.track_goal(sent)
        assert until(sent.done,5.);handle=sent.result();assert handle.accepted,'return Nav2 rejected'
        result=handle.get_result_async()
        assert until(lambda:result.done() or snapshot()['boundary'].get('phase') in ('ACTIVE','FAULT'),5.)
        if not result.done():
            assert snapshot()['boundary'].get('phase')=='ACTIVE',snapshot()['boundary']
            response=call('navigation/release');assert response.success,response.message
        assert until(lambda:result.done() or status().get('phase')=='FAULT' or session.cancel_requested(),180.),'return deadline'
        if session.cancel_requested() or status().get('phase')=='FAULT':
            drain_owned_goals(session,until,extra=(result,))
            raise RuntimeError('return interrupted: '+str(status()))
        assert result.result().status==4,result.result()
        response=call('navigation/idle');assert response.success,response.message
        assert until(lambda:snapshot()['platform'].get('stationary_ready'),10.),'return not physically settled'
        control['set_phase']('PLACE_WAIT')
        assert until(lambda:status().get('transport_stage')=='PLACE' or status().get('phase')=='FAULT',4.)
        assert status().get('transport_stage')=='PLACE',status()
        actual=snapshot()['state'].pose.pose.position
        records.append(dict(event='return_settled',clock_ns=snapshot()['clock_ns'],position=[actual.x,actual.y]))
        session.port.complete('return',dict(session=session.session,position_error_m=math.hypot(actual.x,actual.y)))
        session.await_step('place',until)
        control['set_phase']('LOWER')
        receiving_contact(planner,True,support_name=scenario.planning_support)
        # Place above the receiving support using a fresh RGB-D center; oracle is never read.
        observed=np.array(snapshot()['observation']['point'])
        receiving=np.array([*scenario.receiving_xyz[:2],baseline_z+scenario.receiving_xyz[2]-scenario.target_xyz[2]])
        tcp=planner.tcp();goal=tcp[:3,3]+receiving-observed
        planner.apply_objects([])
        path=planner.cartesian([pose(goal,Rotation.from_matrix(tcp[:3,:3]))])
        assert path is not None,'complete collision-checked place path required'
        planner.execute(path)
        if scenario.support_height_m==0.:
            gate=PlacementSupportGate()
            records.append(dict(event='placement_settle_start',clock_ns=snapshot()['clock_ns'],wall=time.monotonic(),deadline_wall_s=20.))
            def placement_settled():
                current=snapshot();state=status()
                assert state.get('phase')!='FAULT',state
                admit_observation(current['observation'],current['clock_ns'],time.monotonic())
                joints=current['joints'];speeds=dict(zip(joints.name,joints.velocity))
                velocities=[speeds.get('joint'+str(i),float('nan')) for i in range(1,7)]
                ready=(current['platform'].get('stationary_ready') is True
                       and state.get('phase')=='READY' and state.get('transport_stage')=='PLACE')
                return gate.update(current['clock_ns'],velocities,ready,state.get('target_support_N'))
            assert until(placement_settled,20.),'measured floor support/arm settling absent'
            records.append(dict(event='placement_settled',clock_ns=snapshot()['clock_ns'],wall=time.monotonic(),support_N=status()['target_support_N']))
        assert until(lambda:status().get('target_support_N',0.)>.01,5.),'receiving support contact missing'
        start=snapshot()['clock_ns']
        assert until(lambda:snapshot()['clock_ns']-start>=500_000_000,4.)
        assert status().get('target_support_N',0.)>.01,'receiving support lost'
        control['set_phase']('RELEASE');opened=grip(.03)
        assert opened.reached_goal and not opened.stalled,'actual measured gripper opening required'
        def physically_released():
            forces=status().get('gripper_target_contacts',{})
            return all(type(forces.get(f)) in (int,float) and math.isfinite(forces[f]) and 0<=forces[f]<.005 for f in ('link7','link8'))
        assert until(physically_released,3.),'physical release contact persists or unavailable'
        released_ns=snapshot()['clock_ns']
        def released_observation_ready():
            current=snapshot();sample=current['observation']
            try:admit_observation(sample,current['clock_ns'],time.monotonic())
            except ValueError:return False
            return sample['capture_ns']>released_ns
        assert until(released_observation_ready,3.),'fresh original observation after release missing'
        # Remove the attached collision model only after actual release.
        current=snapshot()
        detach_released_cylinder(planner,current['observation'],clock_ns=current['clock_ns'],
            wall=time.monotonic(),released_ns=released_ns)
        receiving_contact(planner,False,support_name=scenario.planning_support)
        control['set_phase']('RETREAT')
        tcp=planner.tcp();back=retreat_point(tcp,scenario)
        path=planner.cartesian([pose(back,Rotation.from_matrix(tcp[:3,:3]))]);assert path is not None
        planner.execute(path)
        assert until(lambda:snapshot()['platform'].get('stationary_ready'),10.)
        start=snapshot()['clock_ns']
        assert until(lambda:snapshot()['clock_ns']-start>=2.2e9,8.)
        session.port.complete('place',dict(session=session.session,clock_ns=snapshot()['clock_ns'],wall=time.monotonic()))
    finally:
        if (not session.goals.drained or result is not None and not result.done()
            or any(r.get('cancel') is not None and not r['cancel'].done() for r in session.goals.rows)):
            drain_owned_goals(session,until,extra=() if result is None else (result,))
        client.destroy()
