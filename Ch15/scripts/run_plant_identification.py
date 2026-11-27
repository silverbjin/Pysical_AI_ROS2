#!/usr/bin/env python3
"""Isolated plant identification. No Nav2, no mission, no actuator bypass.
Exactly one raw TwistStamped publisher, original ingress/gateway/platform.
Same level2 pick-scene model and pinned policy; not a production profile."""
import argparse,hashlib,json,math,os,signal,subprocess,sys,time,traceback
from pathlib import Path

def yaw(q):
    return math.atan2(2*(q[3]*q[6]+q[4]*q[5]),1-2*(q[5]**2+q[6]**2))
def wrap(x):return math.atan2(math.sin(x),math.cos(x))
PULSES=(("yaw_left",0.,.10,4.),("yaw_right",0.,-.10,4.),("low_forward",.035,0.,4.))

def summarize(rows,phase):
    subset=[r for r in rows if phase['start_ns']/1e9<=r['sim_s']<=phase['end_ns']/1e9]
    assert len(subset)>=100,'insufficient engine samples'
    assert all(r['mode']=='ARMED' and not r['fault'] for r in subset)
    pairs=list(zip(subset,subset[1:]))
    dt=[b['sim_s']-a['sim_s'] for a,b in pairs]
    assert all(0<x<=.05 for x in dt),'engine sample gap'
    a,b=subset[0],subset[-1];xy=[b['qpos'][i]-a['qpos'][i] for i in range(2)]
    duration=sum(dt);u=[sum(.5*(x[k]+y[k])*d for (x,y),d in zip(pairs,dt)) for k in ('vx','wz')]
    assert abs(u[0])>=.07 if phase['vx'] else abs(u[1])>=.2,'pulse not delivered'
    if phase['vx']==0:assert max(abs(r['vx']) for r in subset)<1e-9
    if phase['wz']==0:assert max(abs(r['wz']) for r in subset)<1e-9
    assert u[0]*phase['vx']>=0 and u[1]*phase['wz']>=0,'wrong sign'
    return dict(samples=len(subset),duration_sim_s=duration,integrated_command_vx_m=u[0],integrated_command_wz_rad=u[1],
        net_xy_m=math.hypot(*xy),body_forward_m=xy[0]*math.cos(yaw(a['qpos']))+xy[1]*math.sin(yaw(a['qpos'])),
        body_lateral_m=-xy[0]*math.sin(yaw(a['qpos']))+xy[1]*math.cos(yaw(a['qpos'])),
        xy_path_m=sum(math.dist(x['qpos'][:2],y['qpos'][:2]) for x,y in pairs),
        actual_yaw_rad=sum(wrap(yaw(y['qpos'])-yaw(x['qpos'])) for x,y in pairs))

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
    S=dict(source='CH15_ISOLATED_PLANT_IDENTIFICATION_V1',result='FAIL',full_mission_success=False,original_native_l2_pass=False,segment_pass=False,phases=[],checks={})
    children=[];logs=[];node=None;clock=0;state=None;state_wall=0.;statuses={};clients={};vx=wz=0.;origin=None;trace=[]
    def write():
        (out/'plant_result.json').write_text(json.dumps(S,indent=2,allow_nan=False)+'\n')
    def on_clock(m):
        nonlocal clock
        clock=ns(m.clock)
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
        commands=[('ingress',[get_package_prefix('ch13_reuse_wire')+'/lib/ch13_reuse_wire/ingress','--manipulation']),
                  ('gateway',[sys.executable,'-m','ch13_navigation_reuse.command_gateway','--manipulation','true']),
                  ('platform',[sys.executable,'-m','ch13_navigation_reuse.platform_adapter','--repo-root',str(root),'--report',str(out/'engine.json'),'--max-sim-s','50','--scene','vision','--manipulation','true','--pick-scene','true'])]
        for name,cmd in commands:
            log=(out/(name+'.log')).open('w');logs.append(log);children.append((name,subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)))
        rclpy.init();node=Node('ch15_isolated_plant_identification')
        node.create_subscription(Clock,'/clock',on_clock,1)
        node.create_subscription(Odometry,N+'/engine_state',on_state,1)
        for name in ('gateway','platform'):
            node.create_subscription(String,N+'/'+name+'/status',lambda m,n=name:statuses.__setitem__(n,json.loads(m.data)),1)
        pub=node.create_publisher(TwistStamped,N+'/cmd_vel_raw',1);node.create_timer(.02,send)
        assert until(lambda:state is not None and clock>2e9 and statuses.get('gateway',{}).get('ready_for_arm') and stationary() and counts(),35),'startup readiness'
        assert not fault();origin=xy();call('gateway/arm');call('platform/arm')
        for label,command_v,command_w,duration in PULSES:
            assert stationary() and not fault() and counts(),'pulse admission'
            start=xy();r=dict(label=label,vx=command_v,wz=command_w,start_ns=clock,start_pose=[*start,heading()]);S['phases'].append(r);write()
            vx,wz=command_v,command_w
            def check():
                if fault():r['interrupt']='native_fault'
                elif not counts():r['interrupt']='owner_count'
                elif time.monotonic()-state_wall>.3:r['interrupt']='stale_state'
                elif math.dist(xy(),start)>.22 or math.dist(xy(),origin)>.5:r['interrupt']='workspace_envelope'
                return 'interrupt' in r or clock-r['start_ns']>=duration*1e9
            assert until(check,20),'pulse wall timeout'
            vx=wz=0.;r['end_ns']=clock;r['end_pose']=[*xy(),heading()];write()
            assert 'interrupt' not in r,r
            zero=clock
            # Require a fresh stationary indication after pulse; not a cached pre-pulse flag.
            assert until(lambda:clock-zero>=500_000_000 and stationary() or fault(),8),'stop deadline'
            assert stationary() and not fault() and clock-zero<=5e9
            r['settled_ns']=clock;r['settled_pose']=[*xy(),heading()]
            assert math.dist(xy(),start)<=.22 and math.dist(xy(),origin)<=.5
            write()
        S['checks']['one_raw_safe_owner_no_nav2']=counts()
        S['checks']['no_fault']=not fault()
        assert all(S['checks'].values())
        call('platform/shutdown');platform=children[-1][1];platform.wait(timeout=12);assert platform.returncode==0
        e=json.loads((out/'engine.json').read_text());S['checks']['engine_clean']=bool(e['result']=='COMPLETED' and e['normal_shutdown_requested'] and e['rx_joined'] and e['upstream_threads_joined'])
        S['checks']['same_compiled_model']=e['compiled_model_sha256']=='6ab165146bd617a8d99e6e71109bd140a7c9d56d30ddc91b3cf98e66914d25ff'
        rows=[json.loads(l) for l in (out/'engine_observations.jsonl').read_text().splitlines()]
        for r in S['phases']:r['response']=summarize(rows,r)
        S['checks']['three_pulses_measured']=len(S['phases'])==3
        assert all(S['checks'].values())
        S['result']='PASS_SCOPED_IDENTIFICATION'
    except BaseException:S['error']=traceback.format_exc()
    finally:
        vx=wz=0.
        if node is not None and children and alive():
            try:
                until(lambda:False,.2)
                if until(stationary,8):call('platform/shutdown');children[-1][1].wait(timeout=12)
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
        (out/'plant_trace.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in trace))
        write();print(json.dumps(S,indent=2),flush=True)
    return 0 if S['result']=='PASS_SCOPED_IDENTIFICATION' else 1

if __name__=='__main__':sys.exit(main())
