#!/usr/bin/env python3
"""Isolated open-area arc and straight qualification; no Nav2, no mission.
Original ingress/gateway/platform and model; one raw owner. Not production control."""
import argparse,hashlib,json,math,os,signal,subprocess,sys,time,traceback
from pathlib import Path
from startup_window import StartupWindow
from arc_straight_profile import local,arc_command,arc_ready,straight_command,final_ready,arc_point,final_target,ANGLE

def yaw(q):
    return math.atan2(2*(q[3]*q[6]+q[4]*q[5]),1-2*(q[5]**2+q[6]**2))
def wrap(x):return math.atan2(math.sin(x),math.cos(x))
def main():
    p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    a=p.parse_args();root=a.repo_root.resolve();out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=False)
    os.environ.update(CH13_VALIDATION_PROFILE='carry_v1',CH13_VALIDATION_SCENARIO='level2_obstacles',CH13_CAPTURE_OVERLAP='1',CH13_EXPERIMENTAL_SE2='0',CH13_CALLBACK_TIMING='0')
    sys.path.insert(0,str(root/'Ch13/scripts/reuse_13_5'))
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import TwistStamped
    from nav_msgs.msg import Odometry
    from rosgraph_msgs.msg import Clock
    from std_msgs.msg import String
    from std_srvs.srv import Trigger
    from ament_index_python.packages import get_package_prefix
    from ch13_navigation_reuse.command_gateway import N,ns,set_stamp
    from run_r2_probe import service_call
    S=dict(source='CH15_COUPLED_ARC_STRAIGHT_V3',result='FAIL',full_mission_success=False,original_native_l2_pass=False,segment_pass=False,phases=[],checks={})
    children=[];logs=[];node=None;clock=0;state=None;state_wall=0.;safe_stamp=0;safe_wall=0.;safe_zero=False;statuses={};clients={};vx=wz=0.;origin=None;trace=[]
    def write():
        (out/'arc_straight_result.json').write_text(json.dumps(S,indent=2,allow_nan=False)+'\n')
    def on_clock(m):
        nonlocal clock
        clock=ns(m.clock)
    def on_safe(m):
        nonlocal safe_stamp,safe_wall,safe_zero
        stamp=ns(m.header.stamp)
        if stamp>safe_stamp:
            safe_stamp=stamp;safe_wall=time.monotonic()
            safe_zero=m.header.frame_id=='reuse/nav_base' and m.twist.linear.x==0 and m.twist.angular.z==0
    def on_state(m):
        nonlocal state,state_wall
        state=m;state_wall=time.monotonic()
        trace.append(dict(stamp_ns=ns(m.header.stamp),wall=state_wall,xy=xy(),yaw=heading(),requested_vx=vx,requested_wz=wz))
    def xy():return (state.pose.pose.position.x,state.pose.pose.position.y)
    def heading():
        q=state.pose.pose.orientation
        return math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
    def alive():
        return all(c.poll() is None for _,c in children)
    def counts():
        return node.count_publishers(N+'/cmd_vel_raw')==1 and node.count_publishers(N+'/cmd_vel_safe')==1 and node.count_publishers(N+'/nav_cmd')==0 and node.count_publishers(N+'/smoothed_cmd')==0
    def fault():return any(v.get('fault') or v.get('mode')=='FAULT' for v in statuses.values())
    def until(predicate,timeout):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            rclpy.spin_once(node,timeout_sec=.01)
            if predicate():return True
            if not alive():raise RuntimeError('owned process exited early')
        return False
    def call(name):
        r=service_call(node,N+'/'+name,Trigger.Request(),until,clients,timeout=3.)
        assert r.success,(name,r.message)
    def send():
        if clock<=0:return
        m=TwistStamped();set_stamp(m.header.stamp,clock);m.header.frame_id='reuse/nav_base'
        m.twist.linear.x=vx;m.twist.angular.z=wz;pub.publish(m)
    def stationary():return statuses.get('platform',{}).get('stationary_ready') is True
    try:
        subprocess.run([sys.executable,str(root/'Ch13/scripts/reuse_13_8/freeze_runtime.py'),'verify',str(a.manifest.resolve())],check=True)
        S['native_manifest_sha256']=hashlib.sha256(a.manifest.read_bytes()).hexdigest()
        S['profile_sha256']=hashlib.sha256(Path(__file__).with_name('arc_straight_profile.py').read_bytes()).hexdigest()
        S['runner_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        commands=[('ingress',[get_package_prefix('ch13_reuse_wire')+'/lib/ch13_reuse_wire/ingress','--manipulation']),
                  ('gateway',[sys.executable,'-m','ch13_navigation_reuse.command_gateway','--manipulation','true']),
                  ('platform',[sys.executable,'-m','ch13_navigation_reuse.platform_adapter','--repo-root',str(root),'--report',str(out/'engine.json'),'--max-sim-s','60','--scene','vision','--manipulation','true','--pick-scene','true'])]
        # Candidate-only scheduling isolation. Never change Ch13 source,
        # clock stamps, DDS QoS, safety deadlines, or model/policy.
        cpus=sorted(os.sched_getaffinity(0))
        assert len(cpus)>=4,'qualification requires four available CPUs'
        groups={'ingress':cpus[:1],'gateway':cpus[1:2],'platform':cpus[2:]}
        S['cpu_affinity']={**groups,'supervisor':cpus[1:2]}
        for name,cmd in commands:
            env=os.environ.copy()
            if name=='gateway':env['CH13_REUSE_STARTUP_TRACE']=str(out)
            log=(out/(name+'.log')).open('w');logs.append(log)
            command=['taskset','-c',','.join(map(str,groups[name])),*cmd]
            child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=env)
            children.append((name,child))
        os.sched_setaffinity(0,set(cpus[1:2]))
        write()
        rclpy.init();node=Node('ch15_coupled_arc_straight')
        node.create_subscription(Clock,'/clock',on_clock,1)
        node.create_subscription(Odometry,N+'/engine_state',on_state,1)
        node.create_subscription(TwistStamped,N+'/cmd_vel_safe',on_safe,1)
        for name in ('gateway','platform'):
            node.create_subscription(String,N+'/'+name+'/status',lambda m,n=name:statuses.__setitem__(n,json.loads(m.data)),1)
        pub=node.create_publisher(TwistStamped,N+'/cmd_vel_raw',1);node.create_timer(.02,send)
        window=StartupWindow()
        def prearm():
            now=time.monotonic()
            ready=state is not None and clock>2e9 and statuses.get('gateway',{}).get('ready_for_arm') and stationary() and counts() and not fault() and safe_zero and now-state_wall<=.10 and now-safe_wall<=.10
            stamps=(clock,ns(state.header.stamp) if state is not None else 0,safe_stamp)
            return window.observe(now,stamps,ready)
        assert until(lambda: fault() or prearm(),35),'continuous startup readiness'
        S['startup_window_resets']=window.resets
        assert not fault(),('native prearm fault',statuses.get('gateway',{}).get('fault'),statuses.get('platform',{}).get('fault'))
        S['startup_admission']={'stable_wall_s':2.,'min_sim_progress_s':1.,'window_resets':window.resets,'admitted_clock_ns':clock,'safe_stamp_ns':safe_stamp}
        assert not fault();origin=xy()
        call('gateway/arm')
        armed_at=clock
        # Confirm an advancing zero command from the actual armed gateway.
        assert until(lambda:fault() or (statuses.get('gateway',{}).get('mode')=='ARMED' and safe_zero and safe_stamp>armed_at and time.monotonic()-safe_wall<=.10 and stationary()),2),'gateway arm propagation'
        assert not fault(),'native gateway fault during handoff'
        call('platform/arm')
        assert until(lambda:fault() or (statuses.get('platform',{}).get('mode')=='ARMED' and stationary()),2),'platform arm propagation'
        assert not fault()
        S['startup_admission']['both_armed_clock_ns']=clock;write()
        frame=(*xy(),heading());S['frame_origin']=frame
        S['reference_arc_end']=[*arc_point(ANGLE),-ANGLE];S['reference_final']=final_target()
        def observed():return local((*xy(),heading()),frame)
        for label,command,ready_gate,budget in [('clockwise_arc',arc_command,arc_ready,25),('straight',straight_command,final_ready,15)]:
            assert stationary() and not fault() and counts(),'phase admission'
            start=xy();rec=dict(label=label,start_ns=clock,start_local=observed())
            S['phases'].append(rec);write()
            def tick():
                nonlocal vx,wz
                pose=observed()
                if fault():rec['interrupt']='native_fault'
                elif not counts():rec['interrupt']='owner_count'
                elif time.monotonic()-state_wall>.3:rec['interrupt']='stale_state'
                elif math.dist(xy(),origin)>.5:rec['interrupt']='workspace_envelope'
                elif clock-rec['start_ns']>budget*1e9:rec['interrupt']='sim_budget'
                else:
                    cmd=command(pose)
                    if cmd is None:rec['interrupt']='tracking_envelope'
                    else:
                        vx,wz=cmd
                        if cmd==(0.,0.):return True
                if 'interrupt' in rec:vx=wz=0.;rec['interrupt_local']=pose;return True
                return False
            assert until(tick,45),'phase wall timeout'
            vx=wz=0.;rec['end_ns']=clock;rec['end_local']=observed();write()
            assert 'interrupt' not in rec,rec
            zero=clock
            assert until(lambda:(clock-zero>=500_000_000 and stationary()) or fault(),8),'settle deadline'
            assert stationary() and not fault() and clock-zero<=5e9
            rec['settled_ns']=clock;rec['settled_local']=observed()
            rec['ready']=bool(ready_gate(observed()))
            S['checks'][label+'_settled_pose']=rec['ready'];write()
            assert rec['ready'],('measured phase gate',label,rec['settled_local'])
        S['checks']['one_raw_safe_owner_no_nav2']=counts()
        S['checks']['no_fault']=not fault()
        assert all(S['checks'].values())
        call('platform/shutdown');S['shutdown_admission']={'wall':time.monotonic(),'clock_ns':clock};write()
        platform=children[-1][1];platform.wait(timeout=12);assert platform.returncode==0
        e=json.loads((out/'engine.json').read_text());S['checks']['engine_clean']=bool(e['result']=='COMPLETED' and e['normal_shutdown_requested'] and e['rx_joined'] and e['upstream_threads_joined'])
        S['checks']['same_compiled_model']=e['compiled_model_sha256']=='6ab165146bd617a8d99e6e71109bd140a7c9d56d30ddc91b3cf98e66914d25ff'
        rows=[json.loads(l) for l in (out/'engine_observations.jsonl').read_text().splitlines()]
        for rec in S['phases']:
            subset=[x for x in rows if rec['start_ns']/1e9<=x['sim_s']<=rec['end_ns']/1e9]
            assert len(subset)>=100 and all(x['mode']=='ARMED' and not x['fault'] for x in subset)
            dt=[b['sim_s']-a['sim_s'] for a,b in zip(subset,subset[1:])]
            assert all(0<x<=.05 for x in dt)
            rec['engine_samples']=len(subset)
            rec['integrated_vx_m']=sum(.5*(a['vx']+b['vx'])*d for (a,b),d in zip(zip(subset,subset[1:]),dt))
            rec['integrated_wz_rad']=sum(.5*(a['wz']+b['wz'])*d for (a,b),d in zip(zip(subset,subset[1:]),dt))
            rec['engine_max_abs_vx']=max(abs(x['vx']) for x in subset)
            rec['engine_max_abs_wz']=max(abs(x['wz']) for x in subset)
            assert rec['integrated_vx_m']>0
            assert rec['engine_max_abs_vx']<=.0350001 and rec['engine_max_abs_wz']<=.1000001
            if rec['label']=='clockwise_arc':assert rec['integrated_wz_rad']<-.5
        S['checks']['two_actual_phases']=len(S['phases'])==2
        assert all(S['checks'].values())
        S['result']='PASS_SCOPED_ARC_STRAIGHT'
    except BaseException:S['error']=traceback.format_exc()
    finally:
        vx=wz=0.
        if node is not None and children and alive():
            try:
                until(lambda:False,.2)
                if until(stationary,8):
                    call('platform/shutdown');S['shutdown_admission']={'wall':time.monotonic(),'clock_ns':clock};children[-1][1].wait(timeout=12)
            except BaseException:S['cleanup_error']=traceback.format_exc()
        if node is not None:node.destroy_node();rclpy.try_shutdown()
        for name,c in reversed(children):
            if c.poll() is None:
                c.send_signal(signal.SIGINT)
                try:c.wait(timeout=8)
                except subprocess.TimeoutExpired:os.killpg(c.pid,signal.SIGKILL);c.wait(timeout=3)
        for l in logs:l.close()
        S['children']=[dict(name=name,pid=c.pid,exit_code=c.returncode,reaped=c.poll() is not None) for name,c in children]
        S['checks']['children_clean']=len(children)==3 and all(c.returncode==0 for _,c in children)
        if not S['checks']['children_clean']:S['result']='FAIL'
        S['last_status']=statuses
        trace_path=out/'gateway_startup_trace.json'
        S['gateway_startup_trace_present']=trace_path.is_file()
        if trace_path.is_file():
            native_trace=json.loads(trace_path.read_text())
            S['gateway_first_fault']=native_trace.get('fault')
            first=S['gateway_first_fault']
            if first and S['result']=='PASS_SCOPED_ARC_STRAIGHT':
                shutdown=S.get('shutdown_admission')
                # The native gateway may legitimately latch source loss after
                # the owned platform has accepted stationary shutdown. Do not
                # suppress or reset it. Never admit a pre-shutdown fault.
                S['checks']['gateway_fault_after_shutdown_only']=bool(shutdown and first['decision_wall']>=shutdown['wall'] and first['clock_ns']>=shutdown['clock_ns'] and first['reason']=='INPUT_OR_CLOCK_TIMEOUT')
                if not S['checks']['gateway_fault_after_shutdown_only']:S['result']='FAIL'
        elif S['result']=='PASS_SCOPED_ARC_STRAIGHT':S['result']='FAIL'
        (out/'arc_straight_trace.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in trace))
        write();print(json.dumps(S,indent=2),flush=True)
    return 0 if S['result']=='PASS_SCOPED_ARC_STRAIGHT' else 1

if __name__=='__main__':sys.exit(main())
