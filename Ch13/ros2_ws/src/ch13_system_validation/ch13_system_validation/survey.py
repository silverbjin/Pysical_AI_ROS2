"""Known-map survey before fresh vision approach, on the existing ROS owner."""
import math
import time
from rclpy.action import ActionClient
from std_srvs.srv import Trigger
from nav2_msgs.action import NavigateToPose
from ch13_navigation_reuse.command_gateway import N
from ch13_navigation_reuse.nav_contract import prepared_zero
from .continuation import make_navigation_goal,drain_owned_goals


def observe_from_waypoint(session,*,node,until,snapshot,scenario):
    if scenario.survey_pose is None:return
    target=scenario.survey_pose
    client=ActionClient(node,NavigateToPose,'/navigate_to_pose')
    services={};result=None
    def call(name):
        if name not in services:services[name]=node.create_client(Trigger,N+'/'+name)
        service=services[name];assert until(service.service_is_ready,3.),name
        future=service.call_async(Trigger.Request());assert until(future.done,3.),name
        response=future.result();assert response.success,(name,response.message)
    try:
        assert until(client.server_is_ready,3.)
        call('navigation/enable')
        sent=client.send_goal_async(make_navigation_goal(target,snapshot()['clock_ns']))
        session.track_goal(sent);assert until(sent.done,5.)
        handle=sent.result();assert handle.accepted,'survey goal rejected'
        result=handle.get_result_async()
        assert until(lambda:result.done() or prepared_zero(snapshot(),now=time.monotonic()),5.),'survey not prepared at zero'
        assert not result.done(),'survey terminated before motion admission'
        call('gateway/arm');call('platform/arm');call('navigation/release')
        assert until(lambda:result.done() or session.cancel_requested()
                     or snapshot()['boundary'].get('phase')=='FAULT',120.),'survey deadline'
        assert not session.cancel_requested(),'survey canceled'
        assert result.done() and result.result().status==4,'survey navigation failed'
        call('navigation/idle')
        assert until(lambda:snapshot()['platform'].get('stationary_ready') is True,10.),'survey not settled'
        current=snapshot();position=current['state'].pose.pose.position
        session.port.event('survey_terminal_and_settled',goal_id=bytes(handle.goal_id.uuid).hex(),
            target=list(target),position=[position.x,position.y],clock_ns=current['clock_ns'],
            position_error_m=math.hypot(position.x-target[0],position.y-target[1]))
        session.motion_prearmed=True
    finally:
        if not session.goals.drained or result is not None and not result.done():
            drain_owned_goals(session,until,extra=() if result is None else (result,))
        client.destroy()
        for service in services.values():node.destroy_client(service)
