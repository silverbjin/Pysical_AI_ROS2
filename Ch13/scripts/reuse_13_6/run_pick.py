"""Same-engine vision-guided physical picking; oracle is read only after exit."""
import argparse
import json
import os
import sys
import time
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
from ch13_manipulation_reuse.pick_acceptance import assess_pick,assess_held_cancel
from ch13_manipulation_reuse.pick_feedback import lift_correction


def work(*,node,until,snapshot,status,control,out,case='pick',action_client_factory=ActionClient,continuation=None):
    from run_arm_probe import work as warmup
    warmup(node=node,until=until,snapshot=snapshot,status=status,control=control,case='normal',out=out,action_client_factory=action_client_factory)
    refine=False
    if os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1':
        from ch13_system_validation.scenarios import active_scenario
        refine=active_scenario().support_height_m==0.
    planner=Planner(node,until,snapshot,action_client_factory=action_client_factory,refine_execution_scale=refine)
    creation_start=time.monotonic();gripper=action_client_factory(node,GripperCommand,GRIPPER)
    planner.records.append(dict(kind='initialization',step='pick_gripper_client_creation',start_wall=creation_start,end_wall=time.monotonic()))
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
        # Plan both symmetries; rank only routes which satisfy the same timing
        # contract used at execution, rather than comparing raw TOTG durations.
        candidates=[]
        scenario=None
        if os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1':
            from ch13_system_validation.scenarios import active_scenario,grasp_pose
            scenario=active_scenario()
        for sign in (1.,-1.):
            rotation=Rotation.from_matrix(np.column_stack((sign*up,-sign*side,forward)))
            if scenario is not None and scenario.grasp_pitch_down_deg:
                pre,rotation=grasp_pose(center,forward,sign,scenario)
            request.pose=pose(pre,rotation);candidate=planner.plan(pose_goal=request)
            if candidate is not None:
                end=candidate['trajectory'].joint_trajectory.points[-1].time_from_start
                candidates.append((end.sec+end.nanosec/1e9,candidate,rotation,sign))
        assert candidates,'pre-grasp 6D pose planning failed'
        selected=planner.choose_timed_plan([c[1] for c in candidates])
        assert selected is not None,'no pre-grasp candidate satisfies audited execution timing'
        duration,plan,rotation,sign=candidates[selected]
        records.append(dict(pre_grasp_roll_sign=sign,planned_duration_sim_s=duration,
                            equivalent_roll_candidate_durations=[c[0] for c in candidates],
                            grasp_pitch_down_deg=0. if scenario is None else scenario.grasp_pitch_down_deg,
                            pre_distance_m=.12 if scenario is None else scenario.pre_distance_m,
                            selection='shortest_audited_normalized_duration'))
        planner.execute(plan)
        assert until(lambda:snapshot()['platform'].get('stationary_ready'),10.)
        sample,updated=observation();assert np.linalg.norm(updated-center)<.005,'target moved before approach'
        center=updated;baseline_z=float(center[2]);records.append(dict(baseline_observation=sample))
        planner.apply_objects([object_cylinder('pick_target',center)])
        planner.allow_fingers('pick_target',True);phase('GRASP_APPROACH')
        path=planner.cartesian([pose(center,rotation)]);assert path is not None,'full straight approach required'
        planner.execute(path)
        assert until(lambda:snapshot()['platform'].get('stationary_ready'),10.)
        phase('CLOSE');result=grip(0.)
        assert result.stalled,'empty close is not a grasp'
        assert until(lambda:all(status().get('gripper_target_contacts',{}).get(f,0.)>.005 for f in ('link7','link8')),3.),'dual-finger physical contact absent'
        assert until(lambda:status().get('gripper_force_hold',{}).get('ready',False),4.),'bounded contact force hold not established'
        sample,held=observation();planner.attach_observed_cylinder('pick_target',held)
        phase('LIFT')
        current=planner.tcp();lift=current[:3,3]+[0.,0.,.10]
        path=planner.cartesian([pose(lift,Rotation.from_matrix(current[:3,:3]))]);assert path is not None,'full straight lift required'
        if case=='held_cancel':
            planner.execute(path,cancel_after_sim_s=1.)
            records.append(dict(held_cancel=True,actual_terminal='canceled'))
            phase('HOLD');start=snapshot()['clock_ns']
            assert until(lambda:snapshot()['clock_ns']-start>=2.2e9 or status()['phase']=='FAULT',15.)
            assert status()['phase']!='FAULT',status()
            assert status().get('gripper_force_hold',{}).get('ready'), 'cancel released established force hold'
            phase('POST_SETTLE');assert until(lambda:snapshot()['platform'].get('stationary_ready'),10.)
            return
        planner.execute(path)
        from vision_mission import wait_new_capture
        sample=wait_new_capture(until,lambda:snapshot()['observation'],lambda:snapshot()['clock_ns'])
        observed=np.array(sample['point']);deficit=baseline_z+.10-observed[2]
        records.append(dict(visual_lift_observation=sample,observed_lift_m=float(observed[2]-baseline_z)))
        actual=planner.tcp()
        correction=lift_correction(baseline_z,float(observed[2]),float(lift[2]),float(actual[2,3]))
        if correction:
            assert all(status().get('gripper_target_contacts',{}).get(f,0.)>.005 for f in ('link7','link8')),'contact lost before visual correction'
            planner.attach_observed_cylinder('pick_target',observed)
            current=planner.tcp();goal=current[:3,3]+[0.,0.,correction]
            records.append(dict(visual_correction_m=correction,source_capture_ns=sample['capture_ns'],
                                observed_deficit_m=float(deficit),measured_endpoint_lag_m=float(lift[2]-actual[2,3])))
            path=planner.cartesian([pose(goal,Rotation.from_matrix(current[:3,:3]))]);assert path is not None,'visual lift correction path incomplete'
            planner.execute(path)
        # Admission to HOLD uses fresh vision and actual joint velocities,
        # rather than treating the action's coarser goal tolerance as settling.
        settled_since=None
        def lift_settled():
            nonlocal settled_since
            live=snapshot();joints=live['joints'];speeds=dict(zip(joints.name,joints.velocity))
            ready=(live['platform'].get('stationary_ready') and
                   max(abs(speeds['joint'+str(i)]) for i in range(1,7))<=.003 and
                   live['observation']['point'][2]-baseline_z>=.095)
            if not ready:settled_since=None;return False
            if settled_since is None:settled_since=live['clock_ns']
            return live['clock_ns']-settled_since>=500_000_000
        assert until(lift_settled,20.),'fresh visual height/actual velocity settling before HOLD absent'
        phase('HOLD');start=snapshot()['clock_ns']
        assert until(lambda:snapshot()['clock_ns']-start>=2.2e9 or status()['phase']=='FAULT',15.)
        assert status()['phase']!='FAULT',status()
        phase('POST_SETTLE');assert until(lambda:snapshot()['platform'].get('stationary_ready'),10.)
        if continuation is not None:
            continuation(node=node,until=until,snapshot=snapshot,status=status,control=control,
                         planner=planner,grip=grip,baseline_z=baseline_z,records=records,
                         action_client_factory=action_client_factory)
    finally:
        (out/'pick_mission.json').write_text(json.dumps(dict(stages=records,planning=planner.records),indent=2)+'\n')
        gripper.destroy();planner.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo-root',required=True);parser.add_argument('--evidence',required=True)
    parser.add_argument('--case',choices=['pick','held_cancel'],default='pick')
    args=parser.parse_args();out=Path(args.evidence)
    if out.exists() and any(out.iterdir()):raise ValueError('new evidence required')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reuse_13_5'))
    from run_navigation_probe import main as navigate
    from run_handoff import handoff
    result=navigate(['--repo-root',args.repo_root,'--evidence',str(out),'--case','vision','--vision-hz','15'],
        planning=True,pick_scene=True,handoff=lambda **context:handoff(**context,case=args.case,work=lambda **kw:work(**kw,out=out,case=args.case)))
    engine=json.loads((out/'engine.json').read_text())
    physics=engine.get('pick_physics',{})
    assessment=(assess_pick if args.case=='pick' else assess_held_cancel)(physics.get('rows',[]))
    (out/'pick_assessment.json').write_text(json.dumps(assessment,indent=2)+'\n')
    return 0 if result==0 and assessment['result']=='PASS' else 1


if __name__=='__main__':sys.exit(main())
