#!/usr/bin/env python3
"""Ch15 scoped physical approach: original native stack, survey setup, heading stage,
then explicit straight FollowPath. No new velocity publisher or BT mission."""
import argparse, hashlib, json, math, os, re, signal, subprocess, sys, time, traceback
from pathlib import Path
from heading_first_profile import aligned, stage, straight, corridor, final, yaw_error

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo-root',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    a=parser.parse_args();root=a.repo_root.resolve();out=a.evidence.resolve()
    out.mkdir(parents=True,exist_ok=False)
    os.environ.update(CH13_VALIDATION_PROFILE='carry_v1',CH13_VALIDATION_SCENARIO='level2_obstacles',
        CH13_CAPTURE_OVERLAP='1',CH13_EXPERIMENTAL_SE2='0',CH13_CALLBACK_TIMING='0')
    sys.path.insert(0,str(root/'Ch13/scripts/reuse_13_5'))
    import rclpy
    from rclpy.node import Node
    from rclpy.action import ActionClient
    from rclpy.qos import QoSProfile,DurabilityPolicy
    from nav2_msgs.action import NavigateToPose,FollowPath
    from lifecycle_msgs.srv import GetState
    from nav_msgs.msg import Odometry,OccupancyGrid,Path as NavPath
    from geometry_msgs.msg import PoseStamped
    from sensor_msgs.msg import JointState
    from rosgraph_msgs.msg import Clock
    from std_msgs.msg import String
    from std_srvs.srv import Trigger
    from ament_index_python.packages import get_package_share_directory
    from ch13_navigation_reuse.command_gateway import N,ns,set_stamp
    from ch13_navigation_reuse.nav_contract import prepared_zero
    from ch13_navigation_reuse.vision_geometry import admissible
    from ch13_navigation_reuse.path_geometry import path_footprint_clear
    from ch13_navigation_reuse.approach_geometry import position_ik
    from ch13_system_validation.scenarios import get_scenario
    from vision_mission import select_goal,wait_new_capture,current_q
    from run_r2_probe import service_call
    import numpy as np
    S=dict(source='CH15_HEADING_FIRST_V1',scope='actual heading and straight segment only',
           result='FAIL',full_mission_success=False,original_native_l2_pass=False,phases=[],checks={})
    launch=node=log=None;active=None;clients={};armed=False;phase='startup'
    clock=0;state=joints=grid=observation=None;statuses={};rows=[];last_state_wall=0.;plans=[]
    def write():
        (out/'segment_result.json').write_text(json.dumps(S,indent=2,allow_nan=False)+'\n')
    def pose():
        q=state.pose.pose.orientation;p=state.pose.pose.position
        return (p.x,p.y,math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z)))
    def on_state(m):
        nonlocal state,last_state_wall
        state=m;last_state_wall=time.monotonic()
        rows.append(dict(phase=phase,stamp_ns=ns(m.header.stamp),wall=last_state_wall,pose=pose(),
            vx=m.twist.twist.linear.x,wz=m.twist.twist.angular.z,
            boundary_vx=statuses.get('navigation',{}).get('vx'),boundary_wz=statuses.get('navigation',{}).get('wz')))
    def on_clock(m):
        nonlocal clock
        clock=ns(m.clock)
    def on_joints(m):
        nonlocal joints
        joints=m
    def on_observation(m):
        nonlocal observation
        observation=json.loads(m.data)
    def on_grid(m):
        nonlocal grid
        grid=dict(width=m.info.width,height=m.info.height,resolution=m.info.resolution,
                  origin=[m.info.origin.position.x,m.info.origin.position.y],data=list(m.data))
    def until(predicate,timeout):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            rclpy.spin_once(node,timeout_sec=.01)
            if predicate():return True
            if launch.poll() is not None:raise RuntimeError('owned launch exited: '+str(launch.returncode))
        return False
    def call(name,timeout=3):
        r=service_call(node,N+'/'+name,Trigger.Request(),until,clients,timeout=timeout)
        assert r.success,(name,r.message)
    def snapshot():
        return dict(boundary=statuses.get('navigation',{}),gateway=statuses.get('gateway',{}),platform=statuses.get('platform',{}))
    def fault():
        return any(v.get('fault') or v.get('mode')=='FAULT' or v.get('phase')=='FAULT' for k,v in statuses.items() if k!='vision')
    def counts_ok():
        return all(node.count_publishers(t)==1 for t in (N+'/nav_cmd',N+'/smoothed_cmd',N+'/cmd_vel_raw',N+'/cmd_vel_safe'))
    def stamped(p,stamp):
        m=PoseStamped();m.header.frame_id='reuse/map';set_stamp(m.header.stamp,stamp)
        m.pose.position.x,m.pose.position.y=map(float,p[:2])
        m.pose.orientation.z=math.sin(p[2]/2);m.pose.orientation.w=math.cos(p[2]/2)
        return m
    def nav_goal(p,stamp):
        g=NavigateToPose.Goal();g.pose=stamped(p,stamp)
        g.behavior_tree=str(Path(get_package_share_directory('ch13_navigation_reuse'))/'config/navigate_survey.xml')
        return g
    def run_action(label,client,goal,budget,monitor=None):
        nonlocal active,armed,phase
        phase=label;started=clock
        rec=dict(phase=label,start_pose=pose(),start_sim_ns=started)
        S['phases'].append(rec);write()
        assert not fault() and counts_ok() and snapshot()['platform'].get('stationary_ready'),'not ready'
        call('navigation/enable')
        sent=client.send_goal_async(goal);active=(sent,None,None)
        assert until(sent.done,5),'goal admission deadline'
        h=sent.result();assert h.accepted,'goal rejected'
        result=h.get_result_async();active=(sent,h,result);rec['goal_id']=bytes(h.goal_id.uuid).hex()
        assert until(lambda:result.done() or fault() or prepared_zero(snapshot(),already_armed=armed,now=time.monotonic()),5),'prepare deadline'
        assert not result.done() and not fault() and prepared_zero(snapshot(),already_armed=armed,now=time.monotonic()),'not prepared at zero'
        if not armed:
            call('gateway/arm');call('platform/arm');armed=True
        call('navigation/release');rec['release_sim_ns']=clock
        def interrupted():
            if fault():return True
            if clock-started>budget*1e9:return True
            if monitor and (time.monotonic()-last_state_wall>.3 or not monitor(pose())):return True
            return result.done()
        assert until(interrupted,240),'action wall deadline'
        assert result.done() and not fault() and counts_ok() and clock-started<=budget*1e9 and (monitor is None or monitor(pose())),'action interrupted by fault/deadline/corridor'
        rec['terminal']=result.result().status;active=None
        call('navigation/idle');zero=clock
        assert until(lambda:snapshot()['platform'].get('stationary_ready') or fault(),8),'settle deadline'
        assert not fault() and snapshot()['platform'].get('stationary_ready') and clock-zero<=5e9,'settle failed'
        rec.update(settled=True,settled_pose=pose(),settle_sim_ns=clock,stationary_status=snapshot()['platform'])
        write();assert rec['terminal']==4,('action terminal',rec['terminal'])
    try:
        subprocess.run([sys.executable,str(root/'Ch13/scripts/reuse_13_8/freeze_runtime.py'),'verify',str(a.manifest.resolve())],check=True)
        S['native_manifest_sha256']=hashlib.sha256(a.manifest.read_bytes()).hexdigest()
        S['profile_sha256']=hashlib.sha256(Path(__file__).with_name('heading_first_profile.py').read_bytes()).hexdigest()
        S['runner_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        log=(out/'launch.log').open('w')
        launch=subprocess.Popen(['/usr/bin/python3','/opt/ros/jazzy/bin/ros2','launch','ch13_navigation_reuse','navigation.launch.py',
            'repo_root:='+str(root),'report:='+str(out/'engine.json'),'scene:=vision','vision_inference_hz:=15',
            'manipulation:=true','planning:=false','pick_scene:=true','max_sim_s:=360'],
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        rclpy.init();node=Node('ch15_heading_first_segment')
        nav=ActionClient(node,NavigateToPose,'/navigate_to_pose');follow=ActionClient(node,FollowPath,'/follow_path')
        node.create_subscription(Clock,'/clock',on_clock,1)
        node.create_subscription(Odometry,N+'/engine_state',on_state,1)
        node.create_subscription(JointState,N+'/joint_states',on_joints,1)
        node.create_subscription(String,N+'/vision/observation',on_observation,1)
        node.create_subscription(OccupancyGrid,N+'/map',on_grid,QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        for name in ('gateway','platform','navigation','vision'):
            node.create_subscription(String,N+'/'+name+'/status',lambda m,n=name:statuses.__setitem__(n,json.loads(m.data)),1)
        node.create_subscription(NavPath,'/plan',lambda m:plans.append(dict(phase=phase,poses=[[p.pose.position.x,p.pose.position.y] for p in m.poses])),1)
        def ready():
            s=snapshot()
            return state is not None and clock>2e9 and s['gateway'].get('ready_for_arm') and s['boundary'].get('frames_ready') and not s['boundary'].get('pending_future_count',0) and s['platform'].get('stationary_ready') and nav.server_is_ready() and follow.server_is_ready() and counts_ok()
        assert until(lambda:ready() or fault(),35) and ready() and not fault(),'startup readiness'
        for name in ('planner_server','controller_server','velocity_smoother','bt_navigator'):
            end=time.monotonic()+8
            while True:
                r=service_call(node,'/'+name+'/get_state',GetState.Request(),until,clients,GetState)
                if r.current_state.id==3:break
                assert time.monotonic()<end,('lifecycle not active',name)
        scenario=get_scenario('level2_obstacles')
        run_action('survey_setup',nav,nav_goal(scenario.survey_pose,clock),120)
        phase='vision_admission'
        target,record,model=select_goal(root,node,until,lambda:observation,lambda:state,lambda:joints,lambda:grid,lambda:clock)
        S['vision_admission']=record;S['initial_goal']=target
        staging=stage(target);S['stage_goal']=staging
        fp=json.loads((root/'Ch13/ros2_ws/src/ch13_navigation_reuse/config/footprint.json').read_text())['footprint']
        assert path_footprint_clear([staging],grid,fp),'stage footprint blocked'
        assert until(lambda:statuses['navigation'].get('vision_capture_ns',0)>=record['source_observation']['capture_ns'] and statuses['navigation'].get('vision_capture_age_wall_s',1)<=.3,2),'vision health admission'
        call('navigation/require_vision')
        run_action('heading_alignment',nav,nav_goal(staging,clock),90)
        S['checks']['stage_aligned']=aligned(pose(),target)
        assert S['checks']['stage_aligned'],('stage alignment failed',pose(),staging,target)
        phase='fresh_target'
        obs=wait_new_capture(until,lambda:observation,lambda:clock,timeout=3)
        delta=np.array(obs['point'])-np.array(record['source_observation']['point'])
        assert np.linalg.norm(delta)<.03,'target changed'
        target=[target[0]+float(delta[0]),target[1]+float(delta[1]),target[2]]
        S['final_goal']=target;S['fresh_capture_ns']=obs['capture_ns']
        poses=straight(pose(),target)
        S['checks']['straight_map_clear']=bool(path_footprint_clear(poses,grid,fp))
        assert S['checks']['straight_map_clear'],'straight footprint blocked'
        # Reacquire after computational map check; never re-stamp stale capture.
        obs2=wait_new_capture(until,lambda:observation,lambda:clock,timeout=3)
        assert np.linalg.norm(np.array(obs2['point'])-np.array(obs['point']))<.015,'target changed during path validation'
        assert until(lambda:statuses['navigation'].get('vision_capture_ns',0)>=obs2['capture_ns'] and statuses['navigation'].get('vision_capture_age_wall_s',1)<=.3,2),'new capture not received at boundary'
        call('navigation/require_vision')
        path=NavPath();path.header.frame_id='reuse/map';set_stamp(path.header.stamp,clock);path.poses=[stamped(p,clock) for p in poses]
        (out/'straight_path.json').write_text(json.dumps(poses)+'\n')
        goal=FollowPath.Goal();goal.path=path;goal.controller_id='FollowPath';goal.goal_checker_id='goal_checker'
        run_action('straight_approach',follow,goal,45,lambda p:corridor(p,target))
        S['checks']['final_pose']=final(pose(),target)
        S['final_xy_error_m']=math.dist(pose()[:2],target[:2]);S['final_yaw_error_rad']=yaw_error(pose()[2],target[2])
        assert S['checks']['final_pose'],'final measured pose outside unchanged gate'
        obs3=wait_new_capture(until,lambda:observation,lambda:clock,timeout=3)
        S['checks']['fresh_final_observation']=bool(admissible(obs3['capture_ns'],obs3['capture_wall'],clock,time.monotonic(),obs3['tf_stamp_ns']) and np.linalg.norm(np.array(obs3['point'])-np.array(obs2['point']))<.03)
        assert S['checks']['fresh_final_observation']
        S['checks']['workspace']=position_ik(model,current_q(state,joints),obs3['point']) is not None
        S['checks']['one_command_chain']=counts_ok();S['checks']['no_fault']=not fault()
        assert all(S['checks'].values())
        phase='shutdown';call('platform/shutdown');launch.wait(timeout=12)
        engine=json.loads((out/'engine.json').read_text())
        S['checks']['engine_clean']=bool(launch.returncode==0 and engine['normal_shutdown_requested'] and engine['rx_joined'] and engine['upstream_threads_joined'])
        assert S['checks']['engine_clean']
        S['result']='PASS_SCOPED_SEGMENT'
    except BaseException:
        S['error']=traceback.format_exc()
    finally:
        if node is not None and launch is not None and launch.poll() is None:
            try:
                if active is not None:
                    sent,h,result=active
                    if h is None and until(sent.done,3):
                        h=sent.result()
                        if h.accepted:result=h.get_result_async()
                    if h is not None and h.accepted and result is not None and not result.done():
                        c=h.cancel_goal_async();assert until(c.done,3),'cancel ACK timeout'
                        S['cancel_ack']=bool(c.result().goals_canceling)
                        assert until(result.done,3),'cancel terminal timeout'
                        S['cancel_terminal']=result.result().status
                call('navigation/idle',1)
                if until(lambda:snapshot()['platform'].get('stationary_ready'),8):
                    call('platform/shutdown',2);launch.wait(timeout=12)
            except BaseException:S['cleanup_error']=traceback.format_exc()
        if node is not None:node.destroy_node();rclpy.try_shutdown()
        if launch is not None and launch.poll() is None:
            launch.send_signal(signal.SIGINT)
            try:launch.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(launch.pid,signal.SIGKILL);launch.wait(timeout=3)
        if log is not None:log.close()
        if (out/'launch.log').exists():
            t=(out/'launch.log').read_text();pids=re.findall(r'process started with pid \[(\d+)\]',t)
            S['children']=dict(started=len(pids),clean=t.count('process has finished cleanly'),remaining=[int(p) for p in pids if (Path('/proc')/p/'cmdline').exists()],launch_exit=launch.returncode)
            S['checks']['children_clean']=bool(pids) and S['children']['started']==S['children']['clean'] and not S['children']['remaining'] and launch.returncode==0 and 'process has died' not in t
            if not S['checks']['children_clean']:S['result']='FAIL'
        S['last_status']=statuses
        (out/'segment_trace.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        (out/'plans.json').write_text(json.dumps(plans)+'\n')
        write();print(json.dumps(S,indent=2),flush=True)
    return 0 if S['result']=='PASS_SCOPED_SEGMENT' else 1
if __name__=='__main__':sys.exit(main())
