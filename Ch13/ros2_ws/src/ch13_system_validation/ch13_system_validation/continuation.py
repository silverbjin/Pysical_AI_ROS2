"""Same-owner continuation of the live pick, never a new robot process."""
import math
import uuid
import time
import numpy as np
from scipy.spatial.transform import Rotation
from unique_identifier_msgs.msg import UUID
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from ch13_navigation_reuse.command_gateway import set_stamp
from ch13_manipulation_reuse.planning import pose,object_cylinder
from moveit_msgs.msg import AttachedCollisionObject,CollisionObject
from moveit_msgs.srv import ApplyPlanningScene
from .scene_contact import receiving_contact
from .transport import fresh_return_capture
from .fixture import RECEIVING_XY


def drain_owned_goals(session,until,extra=()):
    tracker=session.goals;tracker.cancel()
    def drained():
        tracker.poll()
        return (tracker.drained and all(f.done() for f in extra)
            and all(r.get('cancel') is None or r['cancel'].done() for r in tracker.rows))
    assert until(drained,5.),'owned action send/result/cancel ACK drain deadline'
    assert not tracker.errors,tracker.errors


def continue_mission(*,session,call,node,until,snapshot,status,control,planner,grip,baseline_z,records,action_client_factory=ActionClient):
    session.port.complete('pick',dict(session=session.session))
    session.await_step('return',until)
    identity=uuid.uuid4();home=[0.,0.,math.pi]
    control['reserve_transport'](identity.hex,home);control['set_phase']('CARRY_ARMED')
    assert until(lambda:status().get('phase') in ('CARRY_ARMED','FAULT'),3.)
    assert status()['phase']=='CARRY_ARMED',status()
    client=action_client_factory(node,NavigateToPose,'/navigate_to_pose');handle=None;result=None
    try:
        assert until(client.server_is_ready,3.)
        assert until(lambda:fresh_return_capture(snapshot()['boundary'],time.monotonic()),5.),'fresh original capture headroom before return missing'
        response=call('navigation/require_vision');assert response.success,response.message
        control['set_phase']('CARRY')
        response=call('navigation/enable');assert response.success,response.message
        goal=NavigateToPose.Goal();goal.pose.header.frame_id='reuse/map'
        set_stamp(goal.pose.header.stamp,snapshot()['clock_ns'])
        goal.pose.pose.orientation.z=1.
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
        receiving_contact(planner,True)
        # Place above the receiving support using a fresh RGB-D center; oracle is never read.
        observed=np.array(snapshot()['observation']['point'])
        receiving=np.array([*RECEIVING_XY,baseline_z])
        tcp=planner.tcp();goal=tcp[:3,3]+receiving-observed
        planner.apply_objects([])
        path=planner.cartesian([pose(goal,Rotation.from_matrix(tcp[:3,:3]))])
        assert path is not None,'complete collision-checked place path required'
        planner.execute(path)
        assert until(lambda:status().get('target_support_N',0.)>.01,5.),'receiving support contact missing'
        start=snapshot()['clock_ns']
        assert until(lambda:snapshot()['clock_ns']-start>=500_000_000,4.)
        assert status().get('target_support_N',0.)>.01,'receiving support lost'
        control['set_phase']('RELEASE');grip(.03)
        # Remove the attached collision model only after actual release.
        change=ApplyPlanningScene.Request();change.scene.is_diff=True;change.scene.robot_state.is_diff=True
        attached=AttachedCollisionObject();attached.link_name='reuse/link6';attached.object.id='pick_target';attached.object.operation=CollisionObject.REMOVE
        change.scene.robot_state.attached_collision_objects=[attached]
        change.scene.world.collision_objects=[object_cylinder('pick_target',receiving)]
        assert planner.call('/apply_planning_scene',change).success
        planner.revision+=1
        receiving_contact(planner,False)
        control['set_phase']('RETREAT')
        tcp=planner.tcp();back=tcp[:3,3]+[.08,0.,0.]
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
