#!/usr/bin/env python3
"""Ch15 fixed-world table segment. Single mux before original smoother/boundary/gateway.
Actual survey, explicit entry path, V3 arc and straight. No BT acceptance in this runner."""
import argparse, hashlib, json, math, os, re, signal, subprocess, sys, time, traceback
from pathlib import Path
from table_approach_contract import route,entry_ready,Handoff
from arc_straight_profile import local,arc_command,arc_ready,straight_command,final_ready,wrap
from concurrent.futures import ThreadPoolExecutor
from table_visibility_gate import VisibilityGate,project

def main(argv=None,mission=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo-root',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    a=parser.parse_args(argv);root=a.repo_root.resolve();out=a.evidence.resolve()
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
    from geometry_msgs.msg import PoseStamped,TwistStamped
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
    S=dict(source='CH15_TABLE_V3_SEGMENT_V2',scope='actual table approach only; original native L2 and BT not claimed',
           result='FAIL',full_mission_success=False,original_native_l2_pass=False,phases=[],checks={})
    launch=node=log=None;active=None;clients={};armed=False;phase='startup'
    clock=0;state=joints=grid=observation=local_grid=None;statuses={};rows=[];last_state_wall=0.;plans=[]
    handoff=Handoff();command=(0.,0.);mux=None;mux_last=0;mux_fault='';cost_wall=0.;cost_stamp=0;cost_seq=0;nav2_packets=0;v3_packets=0;cost_checks=[];cost_job=None;cost_good=None
    pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='ch15_geometry')
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
    def on_cost(m):
        nonlocal local_grid,cost_wall,cost_stamp,cost_seq
        stamp=ns(m.header.stamp)
        if stamp<=cost_stamp:return
        q=m.info.origin.orientation
        if m.header.frame_id!='reuse/odom' or abs(q.w-1)>1e-6 or any(abs(v)>1e-6 for v in (q.x,q.y,q.z)):return
        local_grid=dict(width=m.info.width,height=m.info.height,resolution=m.info.resolution,
            origin=[m.info.origin.position.x,m.info.origin.position.y],
            data=[100 if v==100 or v<0 else 0 for v in m.data])
        cost_wall=time.monotonic();cost_stamp=stamp;cost_seq+=1
    def forward(m):
        nonlocal mux_last,mux_fault,nav2_packets
        if handoff.owner!='NAV2':return
        stamp=ns(m.header.stamp)
        # Keep original controller stamp, frame and command. Zero stamped
        # at shutdown is not renewed; native guards remain authoritative.
        if stamp<=0 or stamp<mux_last:return
        vals=(m.twist.linear.x,m.twist.linear.y,m.twist.linear.z,m.twist.angular.x,m.twist.angular.y,m.twist.angular.z)
        if not all(math.isfinite(v) for v in vals):mux_fault='NONFINITE_NAV2';return
        mux.publish(m);mux_last=stamp;nav2_packets+=1
    def emit():
        nonlocal mux_last,v3_packets
        if handoff.owner!='V3' or state is None or not clock:return
        stamp=min(clock,ns(state.header.stamp))
        if stamp<=mux_last:return
        # Do not renew stale source or send nonzero after a supervisor fault.
        if fault() or time.monotonic()-last_state_wall>.10:return
        m=TwistStamped();set_stamp(m.header.stamp,stamp);m.header.frame_id='reuse/nav_base'
        value=(0.,0.) if mission and mission.cancel_requested() else command
        m.twist.linear.x,m.twist.angular.z=value;mux.publish(m);mux_last=stamp;v3_packets+=1
    def until(predicate,timeout):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            rclpy.spin_once(node,timeout_sec=.01)
            if mission:mission.poll_goals()
            if predicate():return True
            if launch.poll() is not None:raise RuntimeError('owned launch exited: '+str(launch.returncode))
        return False
    def call(name,timeout=3):
        r=service_call(node,N+'/'+name,Trigger.Request(),until,clients,timeout=timeout)
        assert r.success,(name,r.message)
    def snapshot():
        return dict(boundary=statuses.get('navigation',{}),gateway=statuses.get('gateway',{}),platform=statuses.get('platform',{}))
    def fault():
        return bool(mux_fault) or any(v.get('fault') or v.get('mode')=='FAULT' or v.get('phase')=='FAULT' for k,v in statuses.items() if k!='vision')
    def counts_ok():
        return all(node.count_publishers(t)==1 for t in ('/ch15/table/nav2_private',N+'/nav_cmd',N+'/smoothed_cmd',N+'/cmd_vel_raw',N+'/cmd_vel_safe'))
    def stamped(p,stamp):
        m=PoseStamped();m.header.frame_id='reuse/map';set_stamp(m.header.stamp,stamp)
        m.pose.position.x,m.pose.position.y=map(float,p[:2])
        m.pose.orientation.z=math.sin(p[2]/2);m.pose.orientation.w=math.cos(p[2]/2)
        return m
    def nav_goal(p,stamp,survey=False):
        g=NavigateToPose.Goal();g.pose=stamped(p,stamp)
        g.behavior_tree=str(Path(get_package_share_directory('ch13_navigation_reuse'))/'config'/('navigate_survey.xml' if survey else 'navigate_no_recovery.xml'))
        return g
    def run_action(label,client,goal,budget,monitor=None):
        nonlocal active,armed,phase
        phase=label;started=clock
        rec=dict(phase=label,start_pose=pose(),start_sim_ns=started,behavior_tree=getattr(goal,'behavior_tree',None),goal_checker=('survey_checker' if label=='survey_setup' else 'goal_checker'))
        S['phases'].append(rec);write()
        assert not fault() and counts_ok() and snapshot()['platform'].get('stationary_ready'),'not ready'
        assert not mission or not mission.cancel_requested(),'BT cancel before new Nav2 action'
        call('navigation/enable')
        assert not mission or not mission.cancel_requested(),'BT cancel before goal send'
        sent=client.send_goal_async(goal);active=(sent,None,None)
        if mission:mission.goal_sent(sent)
        assert until(sent.done,5),'goal admission deadline'
        h=sent.result();assert h.accepted,'goal rejected'
        result=h.get_result_async();active=(sent,h,result);rec['goal_id']=bytes(h.goal_id.uuid).hex()
        assert until(lambda:result.done() or fault() or prepared_zero(snapshot(),already_armed=armed,now=time.monotonic()),5),'prepare deadline'
        assert not result.done() and not fault() and prepared_zero(snapshot(),already_armed=armed,now=time.monotonic()),'not prepared at zero'
        if not armed:
            call('gateway/arm');call('platform/arm');armed=True
        assert not mission or not mission.cancel_requested(),'BT cancel before Nav2 release'
        call('navigation/release');rec['release_sim_ns']=clock
        def interrupted():
            reason=None
            if mission and mission.cancel_requested():reason='BT_CANCEL'
            elif fault():reason='NATIVE_FAULT'
            elif clock-started>budget*1e9:reason='SIM_BUDGET'
            elif monitor and time.monotonic()-last_state_wall>.3:reason='STATE_EXPIRED'
            elif monitor and not monitor(pose()):reason='CANDIDATE_ENVELOPE'
            if reason:
                rec.update(interruption=reason,interruption_pose=pose(),interruption_sim_ns=clock)
                write();return True
            return result.done()
        assert until(interrupted,240),'action wall deadline'
        if result.done():
            rec['terminal']=result.result().status;rec['terminal_sim_ns']=clock
            if mission:mission.goal_terminal(h,rec['terminal'])
        assert result.done() and 'interruption' not in rec and not fault() and counts_ok() and clock-started<=budget*1e9 and (monitor is None or monitor(pose())),'action interrupted by fault/deadline/corridor'
        active=None
        call('navigation/idle');zero=clock
        assert until(lambda:(clock-zero>=500_000_000 and snapshot()['platform'].get('stationary_ready')) or fault(),8),'settle deadline'
        assert not fault() and snapshot()['platform'].get('stationary_ready') and clock-zero<=5e9,'settle failed'
        rec.update(settled=True,settled_pose=pose(),settle_sim_ns=clock,stationary_status=snapshot()['platform'])
        write();assert rec['terminal']==4,('action terminal',rec['terminal'])
    def checked_path(poses,g,fp,timeout=8):
        future=pool.submit(path_footprint_clear,poses,g,fp)
        assert until(lambda:future.done() or fault(),timeout) and future.done() and not fault(),'map check deadline/fault'
        return bool(future.result())
    def local_clear():
        # Evaluate a bounded swept envelope around the measured current pose.
        # At maximum V3 speed .035m/s, 50mm is >1s of travel; angular
        # sweep +/-0.12rad covers stop latency and local check interval.
        nonlocal cost_job,cost_good
        now=time.monotonic()
        if local_grid is None or node.count_publishers('/local_costmap/costmap')!=1:return False
        new_fresh=0<=now-cost_wall<=.65 and -25_000_000<=clock-cost_stamp<=650_000_000
        if cost_job is not None and cost_job[0].done():
            f,started,p,seq,stamp,receipt=cost_job;cost_job=None
            cost_good=(bool(f.result()),started,p,seq,stamp,receipt)
            cost_checks.append(dict(clear=cost_good[0],wall=now,pose=p,cost_seq=seq,source_stamp_ns=stamp,source_receipt_wall=receipt))
        if new_fresh and cost_job is None and (cost_good is None or cost_good[3]!=cost_seq):
            p=pose();x,y,h=p
            # Expanded rectangle covers all translations within 50mm;
            # include 5 orientation samples for bounded yaw drift.
            enlarged=[[a+math.copysign(.05,a),b+math.copysign(.05,b)] for a,b in fp]
            sweep=[(x,y,h+d) for d in (-.12,-.06,0.,.06,.12)]
            cost_job=(pool.submit(path_footprint_clear,sweep,local_grid,enlarged),now,p,cost_seq,cost_stamp,cost_wall)
        return bool(cost_good and cost_good[0] and now-cost_good[1]<=.65 and 0<=now-cost_good[5]<=.65
                    and -25_000_000<=clock-cost_good[4]<=650_000_000
                    and math.dist(pose()[:2],cost_good[2][:2])<=.035
                    and abs(wrap(pose()[2]-cost_good[2][2]))<=.08)
    visibility=VisibilityGate();vision_events=[]
    def vision_admission(source_point):
        now=time.monotonic();b=snapshot()['boundary'];capture_wall=b.get('vision_capture_wall');stamp=b.get('vision_capture_ns',0)
        health=type(capture_wall) in (int,float) and 0<=now-capture_wall<=.3 and -25_000_000<=clock-stamp<=300_000_000
        fresh=bool(observation is not None and admissible(observation['capture_ns'],observation['capture_wall'],clock,now,observation['tf_stamp_ns']))
        shift=float(np.linalg.norm(np.array(observation['point'])-source_point)) if fresh else None
        p,q=state.pose.pose.position,state.pose.pose.orientation
        projection=project(source_point,(p.x,p.y,p.z),(q.x,q.y,q.z,q.w),scenario.camera_pos,scenario.camera_yaw_deg,scenario.camera_pitch_up_deg,record['source_observation']['calibration'])
        ok,reason=visibility.check(now,full_frame=projection['full_frame'],health=health,fresh=fresh,shift=shift)
        if not vision_events or vision_events[-1]['reason']!=reason:
            vision_events.append(dict(reason=reason,ok=ok,clock_ns=clock,wall=now,pose=pose(),projection=projection,health_stamp_ns=stamp,observation_stamp_ns=observation.get('capture_ns') if observation else None,shift_m=shift))
        return ok,reason
    def custom_phase(label,controller,gate,budget,entry,source_point):
        nonlocal command,phase
        phase=label;start=clock
        rec=dict(phase=label,start_pose=pose(),start_sim_ns=start,owner='V3')
        S['phases'].append(rec);write()
        assert not fault() and counts_ok() and snapshot()['platform'].get('stationary_ready')
        assert not mission or not mission.cancel_requested(),'BT cancel before V3 admission'
        command=(0.,0.)
        assert until(lambda:local_clear() or fault(),3) and not fault(),'local costmap admission'
        # Original Ch13 requires fresh capture health continuously. For this
        # static known target only, permit bounded geometric FOV exclusion;
        # reacquire within 300 wall ms after full-frame prediction.
        if label=='straight':
            fresh_observation=wait_new_capture(until,lambda:observation,lambda:clock,timeout=3)
            assert np.linalg.norm(np.array(fresh_observation['point'])-source_point)<.03,'target moved at reacquisition'
            S['checks']['arc_target_reacquired']=True
            S['arc_reacquired_capture_ns']=fresh_observation['capture_ns']
        ok,reason=vision_admission(source_point)
        assert ok,reason
        assert not mission or not mission.cancel_requested(),'BT cancel before V3 enable'
        call('navigation/require_vision');call('navigation/enable')
        assert until(lambda:fault() or prepared_zero(snapshot(),already_armed=True,now=time.monotonic()),5)
        assert not fault() and prepared_zero(snapshot(),already_armed=True,now=time.monotonic()),'V3 held zero not ready'
        assert not mission or not mission.cancel_requested(),'BT cancel before V3 release'
        call('navigation/release');rec['release_sim_ns']=clock
        def tick():
            nonlocal command
            reason=None
            if mission and mission.cancel_requested():reason='BT_CANCEL'
            elif fault():reason='NATIVE_FAULT'
            elif not counts_ok():reason='OWNER_COUNT'
            elif time.monotonic()-last_state_wall>.10:reason='STATE_EXPIRED'
            elif clock-start>budget*1e9:reason='SIM_BUDGET'
            elif not local_clear():reason='LOCAL_COSTMAP_ENVELOPE'
            else:
                ok,why=vision_admission(source_point)
                if not ok:reason=why
                elif label=='straight' and why not in ('OBSERVED','OBSERVED_EDGE'):reason='STRAIGHT_OBSERVATION_LOST'
                else:
                    value=controller(local(pose(),entry))
                    if value is None:reason='TRACKING_ENVELOPE'
                    else:
                        command=value
                        if value==(0.,0.):return True
            if reason:
                command=(0.,0.);rec.update(interruption=reason,interruption_pose=pose(),interruption_sim_ns=clock);write();return True
            return False
        assert until(tick,60),'V3 wall deadline'
        command=(0.,0.);rec.update(end_pose=pose(),end_sim_ns=clock);write()
        assert 'interruption' not in rec,rec
        call('navigation/idle');zero=clock
        assert until(lambda:(clock-zero>=500_000_000 and snapshot()['platform'].get('stationary_ready')) or fault(),8),'V3 settle deadline'
        rec.update(settled=bool(snapshot()['platform'].get('stationary_ready')),settled_pose=pose(),settle_sim_ns=clock)
        rec['ready']=bool(not fault() and clock-zero<=5e9 and rec['settled'] and gate(local(pose(),entry)))
        S['checks'][label+'_settled']=rec['ready'];write();assert rec['ready'],rec
    try:
        subprocess.run([sys.executable,str(root/'Ch13/scripts/reuse_13_8/freeze_runtime.py'),'verify',str(a.manifest.resolve())],check=True)
        S['native_manifest_sha256']=hashlib.sha256(a.manifest.read_bytes()).hexdigest()
        S['profile_sha256']=hashlib.sha256(Path(__file__).with_name('arc_straight_profile.py').read_bytes()).hexdigest()
        S['runner_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        log=(out/'launch.log').open('w')
        launch=subprocess.Popen(['/usr/bin/python3','/opt/ros/jazzy/bin/ros2','launch',str(Path(__file__).with_name('table_navigation.launch.py')),
            'repo_root:='+str(root),'report:='+str(out/'engine.json'),'scene:=vision','vision_inference_hz:=15',
            'manipulation:=true','planning:=false','pick_scene:=true','max_sim_s:=360'],
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        if mission:
            from rclpy.signals import SignalHandlerOptions
            rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
        else:rclpy.init()
        node=Node('ch15_table_segment')
        mux=node.create_publisher(TwistStamped,N+'/nav_cmd',1)
        node.create_subscription(TwistStamped,'/ch15/table/nav2_private',forward,1)
        node.create_timer(.02,emit)
        node.create_subscription(OccupancyGrid,'/local_costmap/costmap',on_cost,QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        nav=ActionClient(node,NavigateToPose,'/navigate_to_pose');follow=ActionClient(node,FollowPath,'/follow_path')
        node.create_subscription(Clock,'/clock',on_clock,1)
        node.create_subscription(Odometry,N+'/engine_state',on_state,1)
        node.create_subscription(JointState,N+'/joint_states',on_joints,1)
        node.create_subscription(String,N+'/vision/observation',on_observation,1)
        node.create_subscription(OccupancyGrid,N+'/map',on_grid,QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        for name in ('gateway','platform','navigation','vision')+(('manipulation',) if mission else ()):
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
        if mission:
            assert until(lambda:bool(statuses.get('manipulation',{}).get('session')) or fault(),3) and not fault(),'actual session missing'
            mission.bind_session(lambda:statuses.get('manipulation',{}))
            S['mission_session']=mission.session;write()
            mission.before_survey(until)
        run_action('survey_setup',nav,nav_goal(scenario.survey_pose,clock,survey=True),120)
        phase='vision_admission'
        target,record,model=select_goal(root,node,until,lambda:observation,lambda:state,lambda:joints,lambda:grid,lambda:clock)
        S['vision_admission']=record;S['initial_goal']=target
        fp=json.loads((root/'Ch13/ros2_ws/src/ch13_navigation_reuse/config/footprint.json').read_text())['footprint']
        # Refresh actual target before fixing it. Do not reanchor to the
        # measured entry pose later.
        obs=wait_new_capture(until,lambda:observation,lambda:clock,timeout=3)
        delta=np.array(obs['point'])-np.array(record['source_observation']['point'])
        assert np.linalg.norm(delta)<.03,'target changed'
        target=[target[0]+float(delta[0]),target[1]+float(delta[1]),target[2]]
        source_point=np.array(obs['point']);S['final_goal']=target
        path=route(pose(),target);entry=path['entry'];S['entry_goal']=entry
        (out/'fixed_world_route.json').write_text(json.dumps(path,indent=2)+'\n')
        # Pinned static map, original filled rectangle + 50mm candidate
        # tracking envelope. This is not a replacement for live costmap.
        enlarged=[[a+math.copysign(.05,a),b+math.copysign(.05,b)] for a,b in fp]
        map_snapshot=grid
        S['checks']['fixed_route_map_clear']=all(checked_path(path[k],map_snapshot,enlarged) for k in ('initial_turn','travel','arc','straight'))
        assert S['checks']['fixed_route_map_clear'],'fixed route blocked'
        obs2=wait_new_capture(until,lambda:observation,lambda:clock,timeout=3)
        assert np.linalg.norm(np.array(obs2['point'])-source_point)<.015,'target changed during map check'
        assert until(lambda:statuses['navigation'].get('vision_capture_ns',0)>=obs2['capture_ns'] and statuses['navigation'].get('vision_capture_age_wall_s',1)<=.3,2)
        call('navigation/require_vision')
        navpath=NavPath();navpath.header.frame_id='reuse/map';set_stamp(navpath.header.stamp,clock)
        navpath.poses=[stamped(p,clock) for p in path['travel']]
        goal=FollowPath.Goal();goal.path=navpath;goal.controller_id='FollowPath';goal.goal_checker_id='goal_checker'
        run_action('entry_travel',follow,goal,90)
        S['checks']['entry_pose']=entry_ready(pose(),entry)
        assert S['checks']['entry_pose'],('entry gate',pose(),entry)
        handoff.switch(goal_terminal=S['phases'][-1]['terminal'],goal_active=active is not None,stationary=snapshot()['platform'].get('stationary_ready'),boundary_phase=snapshot()['boundary'].get('phase'),entry_ok=S['checks']['entry_pose'],chain_ok=counts_ok(),fault=fault())
        S['handoff']={'owner':handoff.owner,'clock_ns':clock,'nav2_terminal_uuid':S['phases'][-1]['goal_id'],'entry_pose':pose()};write()
        custom_phase('clockwise_arc',arc_command,arc_ready,25,entry,source_point)
        custom_phase('straight',straight_command,final_ready,15,entry,source_point)
        S['final_xy_error_m']=math.dist(pose()[:2],target[:2]);S['final_yaw_error_rad']=abs(wrap(pose()[2]-target[2]))
        S['checks']['absolute_final_pose']=S['final_xy_error_m']<=.015 and S['final_yaw_error_rad']<=.06
        assert S['checks']['absolute_final_pose']
        if mission:mission.navigated(until,S,clock)
        obs3=wait_new_capture(until,lambda:observation,lambda:clock,timeout=3)
        S['checks']['fresh_final_observation']=bool(admissible(obs3['capture_ns'],obs3['capture_wall'],clock,time.monotonic(),obs3['tf_stamp_ns']) and np.linalg.norm(np.array(obs3['point'])-source_point)<.03)
        assert S['checks']['fresh_final_observation']
        S['checks']['workspace']=position_ik(model,current_q(state,joints),obs3['point']) is not None
        S['final_observation']=obs3
        if mission:
            assert S['checks']['workspace']
            mission.found(until,obs3,clock,S)
        S['checks']['one_command_chain']=counts_ok();S['checks']['no_fault']=not fault()
        if mission:mission.validate_session();S['checks']['mission_session_stable']=True
        assert all(S['checks'].values())
        phase='shutdown';call('platform/shutdown');S['shutdown_ack']={'wall':time.monotonic(),'clock_ns':clock};launch.wait(timeout=12)
        engine=json.loads((out/'engine.json').read_text())
        S['checks']['engine_clean']=bool(launch.returncode==0 and engine['normal_shutdown_requested'] and engine['rx_joined'] and engine['upstream_threads_joined'])
        assert S['checks']['engine_clean']
        S['checks']['model_identity']=engine.get('compiled_model_sha256')=='6ab165146bd617a8d99e6e71109bd140a7c9d56d30ddc91b3cf98e66914d25ff'
        assert all(S['checks'].values())
        S['result']='PASS_SCOPED_TABLE_SEGMENT'
    except BaseException:
        S['error']=traceback.format_exc()
    finally:
        command=(0.,0.)
        if node is not None and launch is not None and launch.poll() is None:
            try:
                if active is not None:
                    sent,h,result=active
                    if h is None and until(sent.done,3):
                        h=sent.result()
                        if h.accepted:result=h.get_result_async()
                    if h is not None and h.accepted and result is not None and not result.done():
                        c=h.cancel_goal_async();assert until(c.done,3),'cancel ACK timeout'
                        S['cancel_ack']=any(bytes(g.goal_id.uuid)==bytes(h.goal_id.uuid) for g in c.result().goals_canceling)
                        assert until(result.done,3),'cancel terminal timeout'
                        S['cancel_terminal']=result.result().status
                        if mission:mission.goal_terminal(h,S['cancel_terminal'])
                    elif h is not None and h.accepted and result is not None and result.done() and mission:
                        mission.goal_terminal(h,result.result().status)
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
            S['children']=dict(pids=[int(p) for p in pids],started=len(pids),clean=t.count('process has finished cleanly'),remaining=[int(p) for p in pids if (Path('/proc')/p/'cmdline').exists()],launch_exit=launch.returncode)
            S['checks']['children_clean']=bool(pids) and S['children']['started']==S['children']['clean'] and not S['children']['remaining'] and launch.returncode==0 and 'process has died' not in t
            if not S['checks']['children_clean']:S['result']='FAIL'
        if mission:mission.poll_goals()
        pool.shutdown(wait=True,cancel_futures=True)
        S['last_status']=statuses
        S['mux']={'nav2_packets':nav2_packets,'v3_packets':v3_packets,'owner':handoff.owner,'fault':mux_fault}
        (out/'local_cost_checks.json').write_text(json.dumps(cost_checks,indent=2)+'\n')
        (out/'visibility_gate_events.json').write_text(json.dumps(vision_events,indent=2)+'\n')
        (out/'segment_trace.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        (out/'plans.json').write_text(json.dumps(plans)+'\n')
        write();print(json.dumps(S,indent=2),flush=True)
    return 0 if S['result']=='PASS_SCOPED_TABLE_SEGMENT' else 1
if __name__=='__main__':sys.exit(main())
