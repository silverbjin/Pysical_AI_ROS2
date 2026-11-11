"""Actual six-axis/gripper/cancel tests on the same post-navigation engine."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
import numpy as np
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory,GripperCommand
from trajectory_msgs.msg import JointTrajectoryPoint
from ch13_manipulation_reuse.action_bridge import ARM,GRIPPER
from ch13_manipulation_reuse.trajectory import JOINTS

LIMITS=np.array([[-2.618,2.618],[0.,3.14],[-2.697,0.],[-1.832,1.832],[-1.22,1.22],[-3.14,3.14]])


def arm_goal(q,offset=.02):
    start=np.clip(q,LIMITS[:,0],LIMITS[:,1])
    center=np.mean(LIMITS,axis=1)
    target=start+np.where(start<center,offset,-offset)
    goal=FollowJointTrajectory.Goal();goal.trajectory.joint_names=list(JOINTS)
    for t,positions in [(0,start),(2,target),(4,start)]:
        point=JointTrajectoryPoint();point.time_from_start.sec=t
        point.positions=positions.tolist();point.velocities=[0.]*6;point.accelerations=[0.]*6
        goal.trajectory.points.append(point)
    return goal


def work(*,node,until,snapshot,status,control,case,out,action_client_factory=ActionClient):
    records=[];started=time.monotonic()
    terminal_timeout=240. if os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1' and case=='normal' else 20.
    records.append(dict(kind='action_wait_budget',case=case,wall_s=terminal_timeout))
    arm=action_client_factory(node,FollowJointTrajectory,ARM)
    if os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1':
        records.append(dict(kind='initialization',step='warmup_arm_client',start_wall=started,end_wall=time.monotonic()))
    started=time.monotonic()
    gripper=action_client_factory(node,GripperCommand,GRIPPER)
    if os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1':
        records.append(dict(kind='initialization',step='warmup_gripper_client',start_wall=started,end_wall=time.monotonic()))
    def measured():
        joints=snapshot()['joints'];values=dict(zip(joints.name,joints.position))
        return np.array([values[j] for j in JOINTS]),values
    def send(client,goal):
        sent=client.send_goal_async(goal)
        assert until(sent.done,3.),'action goal response deadline'
        handle=sent.result();assert handle.accepted,'actual action rejected'
        return handle,handle.get_result_async()
    try:
        assert until(lambda:arm.server_is_ready() and gripper.server_is_ready(),3.)
        q,_=measured();handle,result=send(arm,arm_goal(q))
        if case in ('cancel','loss'):
            initial_clock=snapshot()['clock_ns']
            assert until(lambda:snapshot()['clock_ns']-initial_clock>=800_000_000,3.)
            if case=='cancel':
                canceled=handle.cancel_goal_async();assert until(canceled.done,3.)
                assert canceled.result().goals_canceling,'cancel ACK absent'
            else:control['disable_heartbeat']()
        assert until(result.done,terminal_timeout),'measured arm terminal deadline'
        terminal=result.result();expected={'normal':4,'cancel':5,'loss':6}[case]
        assert terminal.status==expected,(terminal.status,terminal.result.error_string,status())
        q_after,_=measured()
        records.append(dict(kind='arm',case=case,status=terminal.status,error_code=terminal.result.error_code,
                            reason=terminal.result.error_string,start=q.tolist(),final=q_after.tolist()))
        assert until(lambda:snapshot()['platform'].get('stationary_ready'),8.),'actual post-arm settling missing'
        if case=='normal':
            for target in (.03,0.):
                request=GripperCommand.Goal();request.command.position=target;request.command.max_effort=.5
                grip_handle,grip_result=send(gripper,request)
                assert until(grip_result.done,terminal_timeout),'gripper measured terminal deadline'
                response=grip_result.result();assert response.status==4
                assert response.result.reached_goal and not response.result.stalled
                _,values=measured()
                assert abs(values['joint7']-target)<=.002
                assert abs(values['joint8']+values['joint7'])<=.002
                records.append(dict(kind='gripper',target=target,status=response.status,
                                    joint7=values['joint7'],joint8=values['joint8'],effort=response.result.effort))
        if case=='loss':assert status()['phase']=='FAULT' and status()['fault']=='MISSION_EXPIRED'
    finally:
        (out/'arm_probe.json').write_text(json.dumps(dict(case=case,records=records),indent=2)+'\n')
        arm.destroy();gripper.destroy()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo-root',required=True)
    parser.add_argument('--evidence',required=True);parser.add_argument('--case',choices=['normal','cancel','loss'],default='normal')
    args=parser.parse_args();out=Path(args.evidence)
    if out.exists() and any(out.iterdir()):raise ValueError('new evidence directory required')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reuse_13_5'))
    from run_navigation_probe import main as navigate
    from run_handoff import handoff
    def callback(**context):
        return handoff(**context,case='arm_'+args.case,
                       work=lambda **kw:work(**kw,case=args.case,out=out))
    return navigate(['--repo-root',args.repo_root,'--evidence',str(out),'--case','vision','--vision-hz','15'],handoff=callback)


if __name__=='__main__':sys.exit(main())
