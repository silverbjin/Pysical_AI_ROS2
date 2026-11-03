"""Real MoveIt planning, rejection, Cartesian motion and execution on live engine."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from rclpy.action import ActionClient
from control_msgs.action import GripperCommand
from geometry_msgs.msg import PoseStamped
from moveit_msgs.msg import CollisionObject
from moveit_msgs.srv import GetStateValidity
from rosidl_runtime_py.convert import message_to_ordereddict
from ch13_manipulation_reuse.action_bridge import GRIPPER
from ch13_manipulation_reuse.planning import Planner,pose,object_box
from ch13_navigation_reuse.command_gateway import set_stamp
from ch13_navigation_reuse.scene import layout


def work(*,node,until,snapshot,status,control,out):
    from run_arm_probe import work as arm_work
    arm_work(node=node,until=until,snapshot=snapshot,status=status,control=control,case='normal',out=out)
    assert until(lambda:snapshot()['platform'].get('stationary_ready') and status()['phase']=='READY',5.)
    gripper=ActionClient(node,GripperCommand,GRIPPER)
    assert until(gripper.server_is_ready,3.)
    request=GripperCommand.Goal();request.command.position=.03;request.command.max_effort=.5
    sent=gripper.send_goal_async(request);assert until(sent.done,3.);handle=sent.result();assert handle.accepted
    result=handle.get_result_async();assert until(result.done,15.);assert result.result().status==4
    gripper.destroy()
    planner=Planner(node,until,snapshot);measurements=[]
    validity=node.create_client(GetStateValidity,'/check_state_validity')
    def valid_state():
        assert until(validity.service_is_ready,3.)
        request=GetStateValidity.Request();request.robot_state=planner.start_state();request.group_name='manipulator_arm'
        future=validity.call_async(request);assert until(future.done,3.)
        response=future.result();contacts=[message_to_ordereddict(c) for c in response.contacts]
        planner.records.append(dict(kind='state_validity',valid=response.valid,contacts=contacts))
        return response.valid,contacts
    try:
        objects=[object_box('ground',[0.,0.,-.01],[20.,20.,.02])]
        objects += [object_box('reuse_'+name,center,2*np.array(size)) for name,center,size in layout('vision')]
        planner.apply_objects(objects)
        q=planner.joints();target=q+np.array([.04,.04,-.04,.04,-.04,.04])
        plan=planner.plan(joint_goal=target);assert plan is not None,'MoveIt joint planning failed'
        predicted=planner.tcp(target)
        planner.execute(plan)
        assert until(lambda:snapshot()['platform'].get('stationary_ready'),8.)
        actual=planner.tcp();position_error=float(np.linalg.norm(actual[:3,3]-predicted[:3,3]))
        rotation_error=float(Rotation.from_matrix(predicted[:3,:3].T@actual[:3,:3]).magnitude())
        measurements.append(dict(case='joint_plan_execute',position_error_m=position_error,orientation_error_rad=rotation_error))
        assert position_error<=.01 and rotation_error<=.05,measurements[-1]
        reachable=planner.tcp(planner.joints()+np.array([.02,.02,-.02,.02,-.02,.02]))
        target_pose=PoseStamped();target_pose.header.frame_id='reuse/odom'
        set_stamp(target_pose.header.stamp,snapshot()['observation']['capture_ns'])
        target_pose.pose=pose(reachable[:3,3],Rotation.from_matrix(reachable[:3,:3]))
        pose_plan=planner.plan(pose_goal=target_pose);assert pose_plan is not None,'reachable pose IK/planning failed'
        planner.execute(pose_plan)
        assert until(lambda:snapshot()['platform'].get('stationary_ready'),8.)
        actual=planner.tcp()
        pose_error=float(np.linalg.norm(actual[:3,3]-reachable[:3,3]))
        orientation_error=float(Rotation.from_matrix(reachable[:3,:3].T@actual[:3,:3]).magnitude())
        measurements.append(dict(case='pose_plan_execute',position_error_m=pose_error,orientation_error_rad=orientation_error))
        assert pose_error<=.01 and orientation_error<=.05
        unreachable=PoseStamped();unreachable.header.frame_id='reuse/odom'
        set_stamp(unreachable.header.stamp,snapshot()['observation']['capture_ns']);unreachable.pose=pose([100.,0.,.5])
        assert planner.plan(pose_goal=unreachable) is None,'unreachable pose accepted'
        current=planner.tcp()
        assert valid_state()[0],'actual start state already colliding'
        blocker=object_box('planning_collision_fixture',current[:3,3],[.15,.15,.15])
        planner.apply_objects([blocker]);valid,contacts=valid_state()
        assert not valid and 'planning_collision_fixture' in json.dumps(contacts),'fixture collision not independently identified'
        assert planner.plan(joint_goal=planner.joints()) is None,'collision fixture ignored'
        blocker.operation=CollisionObject.REMOVE;planner.apply_objects([blocker])
        assert valid_state()[0],'collision fixture removal failed'
        current=planner.tcp();target=current[:3,3]+[.005,0.,0.]
        straight=planner.cartesian([pose(target,Rotation.from_matrix(current[:3,:3]))])
        assert straight is not None,'Cartesian path incomplete'
        planner.execute(straight)
        assert until(lambda:snapshot()['platform'].get('stationary_ready'),8.)
        residual=float(np.linalg.norm(planner.tcp()[:3,3]-target));measurements.append(dict(case='cartesian_execute',position_error_m=residual))
        assert residual<=.01
        plan=planner.plan(joint_goal=planner.joints()+np.array([.08,.04,-.04,.04,-.04,.04]))
        assert plan is not None
        planner.execute(plan,cancel_after_sim_s=.3)
        assert until(lambda:snapshot()['platform'].get('stationary_ready'),8.)
    finally:
        (out/'moveit_probe.json').write_text(json.dumps(dict(records=planner.records,measurements=measurements),indent=2)+'\n')
        node.destroy_client(validity)
        planner.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo-root',required=True);parser.add_argument('--evidence',required=True)
    args=parser.parse_args();out=Path(args.evidence)
    if out.exists() and any(out.iterdir()):raise ValueError('new evidence directory required')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reuse_13_5'))
    from run_navigation_probe import main as navigate
    from run_handoff import handoff
    return navigate(['--repo-root',args.repo_root,'--evidence',str(out),'--case','vision','--vision-hz','15'],
                    planning=True,handoff=lambda **context:handoff(**context,case='moveit',work=lambda **kw:work(**kw,out=out)))


if __name__=='__main__':sys.exit(main())
