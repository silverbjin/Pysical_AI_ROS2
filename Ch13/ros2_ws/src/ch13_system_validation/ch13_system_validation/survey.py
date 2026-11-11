"""Known-map survey before fresh vision approach, on the existing ROS owner."""
import math
import time
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from rclpy.action import ActionClient
from std_srvs.srv import Trigger
from nav2_msgs.action import NavigateToPose
from ch13_navigation_reuse.command_gateway import N
from ch13_navigation_reuse.nav_contract import prepared_zero
from .continuation import make_navigation_goal,drain_owned_goals
from .survey_budget import SurveyBudget,WALL_SECONDS


def make_survey_goal(target, clock_ns):
    goal=make_navigation_goal(target,clock_ns)
    path=Path(get_package_share_directory('ch13_navigation_reuse'))/'config/navigate_survey.xml'
    if not path.is_file():
        raise ValueError('installed survey behavior tree missing')
    goal.behavior_tree=str(path)
    return goal


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
        sent=client.send_goal_async(make_survey_goal(target,snapshot()['clock_ns']))
        session.track_goal(sent);assert until(sent.done,5.)
        handle=sent.result();assert handle.accepted,'survey goal rejected'
        result=handle.get_result_async()
        assert until(lambda:result.done() or prepared_zero(snapshot(),now=time.monotonic()),5.),'survey not prepared at zero'
        assert not result.done(),'survey terminated before motion admission'
        call('gateway/arm');call('platform/arm');call('navigation/release')
        budget=SurveyBudget(clock_ns=snapshot()['clock_ns'],wall=time.monotonic())
        def stopped():
            if result.done() or session.cancel_requested():return True
            current=snapshot()
            return (current['boundary'].get('phase')=='FAULT'
                    or budget.reason(clock_ns=current['clock_ns'],wall=time.monotonic()) is not None)
        budget.record_start(session.port)
        assert until(stopped,WALL_SECONDS),'survey wall deadline'
        assert budget.reason(clock_ns=snapshot()['clock_ns'],wall=time.monotonic()) is None,'survey duration deadline'
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
