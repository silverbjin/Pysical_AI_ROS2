"""Same-engine vision-guided physical picking; oracle is read only after exit."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from geometry_msgs.msg import PoseStamped
from rclpy.action import ActionClient
from control_msgs.action import GripperCommand
from ch13_navigation_reuse.command_gateway import set_stamp
from ch13_navigation_reuse.scene import layout
from ch13_manipulation_reuse.planning import Planner,pose,object_box,object_cylinder
from ch13_manipulation_reuse.action_bridge import GRIPPER
from ch13_manipulation_reuse.pick_acceptance import assess_pick


def work(*,node,until,snapshot,status,control,out):
    from run_arm_probe import work as warmup
    warmup(node=node,until=until,snapshot=snapshot,status=status,control=control,case='normal',out=out)
    planner=Planner(node,until,snapshot);gripper=ActionClient(node,GripperCommand,GRIPPER)
    records=[]
    def phase(value):
        control['set_phase'](value)
        records.append(dict(phase=value,clock_ns=snapshot()['clock_ns']))
    def grip(position):
        assert until(gripper.server_is_ready,3.)
        request=GripperCommand.Goal();request.command.position=position;request.command.max_effort=.5
        sent=gripper.send_goal_async(request);assert until(sent.done,3.)
        handle=sent.result();assert handle.accepted
        result=handle.get_result_async();assert until(result.done,25.),'gripper measured terminal deadline'
        assert result.result().status==4,result.result()
        records.append(dict(gripper_position=result.result().result.position,stalled=result.result().result.stalled,
                            reached=result.result().result.reached_goal))
        return result.result().result
    def observation():
        sample=snapshot()['observation'];assert 'cylinder_fit' in sample,'known cylinder RGB-D fit required'
        assert sample['source']=='actual_Renderer_RGBD_known_upright_cylinder_fit'
        return sample,np.array(sample['point'])
    try:
        grip(.03);phase('PRE_GRASP')
        sample,center=observation()
        objects=[object_box('ground',[0.,0.,-.01],[20.,20.,.02])]
        objects += [object_box('reuse_'+name,c,2*np.array(size)) for name,c,size in layout('vision') if name!='target']
        objects.append(object_cylinder('pick_target',center));planner.apply_objects(objects)
        root=snapshot()['state'].pose.pose.position
        forward=center-np.array([root.x,root.y,center[2]]);forward/=np.linalg.norm(forward)
        up=np.array([0.,0.,1.]);side=np.cross(up,forward)
        pre=center-.12*forward
        request=PoseStamped();request.header.frame_id='reuse/odom'
        set_stamp(request.header.stamp,sample['capture_ns'])
        # An upright cylinder has two equivalent finger roll orientations.
        # Plan both geometric symmetries and choose the shorter valid route;
        # do not force a nearly pi wrist rotation from the current state.
        candidates=[]
        for sign in (1.,-1.):
            rotation=Rotation.from_matrix(np.column_stack((sign*up,-sign*side,forward)))
            request.pose=pose(pre,rotation);candidate=planner.plan(pose_goal=request)
            if candidate is not None:
                end=candidate['trajectory'].joint_trajectory.points[-1].time_from_start
                candidates.append((end.sec+end.nanosec/1e9,candidate,rotation,sign))
        assert candidates,'pre-grasp 6D pose planning failed'
        duration,plan,rotation,sign=min(candidates,key=lambda c:c[0])
        records.append(dict(pre_grasp_roll_sign=sign,planned_duration_sim_s=duration,
                            equivalent_roll_candidate_durations=[c[0] for c in candidates]))
        planner.execute(plan)
        assert until(lambda:snapshot()['platform'].get('stationary_ready'),10.)
        sample,updated=observation();assert np.linalg.norm(updated-center)<.005,'target moved before approach'
        center=updated;planner.apply_objects([object_cylinder('pick_target',center)])
        planner.allow_fingers('pick_target',True);phase('GRASP_APPROACH')
        path=planner.cartesian([pose(center,rotation)]);assert path is not None,'full straight approach required'
        planner.execute(path)
        assert until(lambda:snapshot()['platform'].get('stationary_ready'),10.)
        phase('CLOSE');result=grip(0.)
        assert result.stalled,'empty close is not a grasp'
        assert until(lambda:all(status().get('gripper_target_contacts',{}).get(f,0.)>.005 for f in ('link7','link8')),3.),'dual-finger physical contact absent'
        sample,held=observation();planner.attach_observed_cylinder('pick_target',held)
        phase('LIFT')
        current=planner.tcp();lift=current[:3,3]+[0.,0.,.10]
        path=planner.cartesian([pose(lift,Rotation.from_matrix(current[:3,:3]))]);assert path is not None,'full straight lift required'
        planner.execute(path)
        phase('HOLD');start=snapshot()['clock_ns']
        assert until(lambda:snapshot()['clock_ns']-start>=2.2e9 or status()['phase']=='FAULT',15.)
        assert status()['phase']!='FAULT',status()
        phase('POST_SETTLE');assert until(lambda:snapshot()['platform'].get('stationary_ready'),10.)
    finally:
        (out/'pick_mission.json').write_text(json.dumps(dict(stages=records,planning=planner.records),indent=2)+'\n')
        gripper.destroy();planner.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo-root',required=True);parser.add_argument('--evidence',required=True)
    args=parser.parse_args();out=Path(args.evidence)
    if out.exists() and any(out.iterdir()):raise ValueError('new evidence required')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reuse_13_5'))
    from run_navigation_probe import main as navigate
    from run_handoff import handoff
    result=navigate(['--repo-root',args.repo_root,'--evidence',str(out),'--case','vision','--vision-hz','15'],
        planning=True,pick_scene=True,handoff=lambda **context:handoff(**context,case='pick',work=lambda **kw:work(**kw,out=out)))
    engine=json.loads((out/'engine.json').read_text())
    physics=engine.get('pick_physics',{})
    assessment=assess_pick(physics.get('rows',[]))
    (out/'pick_assessment.json').write_text(json.dumps(assessment,indent=2)+'\n')
    return 0 if result==0 and assessment['result']=='PASS' else 1


if __name__=='__main__':sys.exit(main())
