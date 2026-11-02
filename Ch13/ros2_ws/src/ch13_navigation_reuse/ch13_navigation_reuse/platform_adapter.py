"""Adapter around the pinned upstream loop; never implements a new walking controller."""
import argparse,builtins,difflib,hashlib,importlib.util,inspect,json,math,os,sys,textwrap,threading,time,traceback,types
from pathlib import Path
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.clock import Clock as TimerClock
from rclpy.clock_type import ClockType
from rcl_interfaces.msg import SetParametersResult
from std_srvs.srv import Trigger
from std_msgs.msg import String
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from rosgraph_msgs.msg import Clock
from tf2_msgs.msg import TFMessage
from scipy.spatial.transform import Rotation
from .command_gateway import N,JOINT_NAMES,ns,gid,set_stamp
from .safety import Guard
from .state_adapter import adapt
from .wire import decode

class Platform(Node):
    def __init__(self):
        super().__init__('ch13_reuse_platform')
        self.lock=threading.RLock();self.guard=Guard(required=('safe',),control='safe')
        self.stationary_ready=False;self.stationary_start=None;self.last_capture_wall=None;self.pending_arm=0.;self.last_arm_wall=-1e9
        self.allow_tf_broadcasters=False;self.stop_requested=False;self.last_state=None;self.previous_mode=None;self.events=[]
        self.clock_pub=self.create_publisher(Clock,'/clock',1)
        self.base_pub=self.create_publisher(Odometry,N+'/engine_state',1)
        self.nav_pub=self.create_publisher(Odometry,N+'/odometry',1)
        self.joint_pub=self.create_publisher(JointState,N+'/joint_states',1)
        self.tf_pub=self.create_publisher(TFMessage,'/tf',1)
        self.status_pub=self.create_publisher(String,N+'/platform/status',1)
        self.create_subscription(String,N+'/ingress/platform',self.on_packet,16)
        self.create_service(Trigger,N+'/platform/arm',self.on_arm)
        self.create_service(Trigger,N+'/platform/reset',self.on_reset)
        self.create_service(Trigger,N+'/platform/shutdown',self.on_shutdown)
        self.declare_parameter('arm_joint1_offset',0.)
        self.add_on_set_parameters_callback(self.on_parameters)
        self.timer=self.create_timer(.02,self.monitor,clock=TimerClock(clock_type=ClockType.STEADY_TIME))
    def on_packet(self,packet):
        with self.lock:
            try:
                key,msg,info=decode(packet.data)
                if key!='safe':raise ValueError('unexpected ingress channel')
                if not self.guard._owner('relay',info['relay_gid']):return
                v,w=msg.twist.linear,msg.twist.angular
                self.guard.command(ns(msg.header.stamp),info['receipt_wall'],gid(info),(v.x,v.y,v.z,w.x,w.y,w.z),msg.header.frame_id)
            except (ValueError,KeyError,TypeError) as exc:self.guard.trip('INVALID_INGRESS:'+type(exc).__name__)
    def on_arm(self,request,response):
        with self.lock:
            response.success=self.guard.arm(time.monotonic());response.message=json.dumps({'mode':self.guard.mode,'fault':self.guard.fault,'counts':self.guard.counts})
        return response
    def on_reset(self,request,response):
        with self.lock:self.guard.reset();self.stationary_ready=False;self.stationary_start=None
        response.success=True;response.message='DISARMED; fresh zero and explicit arm required';return response
    def on_shutdown(self,request,response):
        with self.lock:
            response.success=self.ready_now() and self.guard.last_values==(0.,0.)
            if response.success:self.stop_requested=True
            response.message='settled shutdown accepted' if response.success else 'actual stationary zero required'
        return response
    def on_parameters(self,parameters):
        with self.lock:
            for p in parameters:
                if p.name!='arm_joint1_offset':return SetParametersResult(successful=False,reason='unsupported live parameter')
                if not isinstance(p.value,float) or not math.isfinite(p.value) or abs(p.value)>.05:return SetParametersResult(successful=False,reason='finite joint1 offset within0.05rad required')
                if not self.ready_now() or self.guard.mode!='ARMED' or self.guard.last_values!=(0.,0.):return SetParametersResult(successful=False,reason='actual settled zero and armed platform required')
                if time.monotonic()-self.last_arm_wall<.2:return SetParametersResult(successful=False,reason='arm target rate max5Hz')
            for p in parameters:self.pending_arm=p.value
            self.last_arm_wall=time.monotonic();self.stationary_ready=False;self.stationary_start=None
            self.events.append({'event':'arm_hold_target','offset':self.pending_arm,'wall':self.last_arm_wall})
        return SetParametersResult(successful=True)
    def ready_now(self):
        return self.stationary_ready and self.last_capture_wall is not None and 0<=time.monotonic()-self.last_capture_wall<=.30
    def monitor(self):
        queried_wall=time.monotonic()
        counts={'clock':self.count_publishers('/clock'),'safe':self.count_publishers(N+'/cmd_vel_safe'),'relay':self.count_publishers(N+'/ingress/platform')}
        if not self.allow_tf_broadcasters:counts['tf']=self.count_publishers('/tf')
        with self.lock:
            now=time.monotonic();self.guard.graph(counts,queried_wall);decision=self.guard.output(now)
            status={'mode':decision.mode,'fault':decision.fault,'stationary_ready':self.ready_now(),'clock_ns':self.guard.clock_ns,'vx':decision.vx,'wz':decision.wz,'arm_joint1_target':self.pending_arm,'counts':self.guard.counts}
            changed=self.previous_mode!=decision.mode;self.previous_mode=decision.mode
        # DDS graph/publish/log operations may block; never hold the physics-state lock.
        self.status_pub.publish(String(data=json.dumps(status)))
        if changed:self.get_logger().info('mode='+decision.mode+' '+decision.fault)
    def engine_command(self,sim_ns):
        with self.lock:
            self.guard.clock(sim_ns,time.monotonic(),'owned_engine')
            return self.guard.output(time.monotonic()),self.pending_arm
    def capture(self,p,sim_ns,wall,decision):
        q=p.mjData.qpos.copy();v=p.mjData.qvel.copy();s=adapt(q,v,JOINT_NAMES,sim_ns)
        tilt=math.acos(float(np.clip(1-2*(q[4]**2+q[5]**2),-1,1)))
        with self.lock:
            if self.last_capture_wall is not None and wall-self.last_capture_wall>.30:self.stationary_start=None;self.stationary_ready=False
            self.last_capture_wall=wall
            good=(decision.vx==0 and decision.wz==0 and np.linalg.norm(v[:2])<=.05 and abs(v[5])<=.20 and np.max(abs(v[18:24]))<=.20 and np.max(abs(q[19:25]-p.desired_joint_pos_arm))<=.10 and tilt<=.35)
            if good:
                if self.stationary_start is None:self.stationary_start=(wall,sim_ns,q.copy(),s['yaw'])
                anchor=self.stationary_start
                if np.linalg.norm(q[:2]-anchor[2][:2])>.03 or abs(math.atan2(math.sin(s['yaw']-anchor[3]),math.cos(s['yaw']-anchor[3])))>.10 or np.max(abs(q[19:25]-anchor[2][19:25]))>.05:self.stationary_start=None;self.stationary_ready=False
                else:self.stationary_ready=wall-anchor[0]>=1. and sim_ns-anchor[1]>=500_000_000
            else:self.stationary_start=None;self.stationary_ready=False
            self.last_state=s
        return q,v,s,tilt
    def publish_state(self,p,s):
        value=s['stamp_ns'];c=Clock();set_stamp(c.clock,value);self.clock_pub.publish(c)
        def odom(child,position,quat,linear,angular):
            o=Odometry();set_stamp(o.header.stamp,value);o.header.frame_id='reuse/odom';o.child_frame_id=child
            o.pose.pose.position.x,o.pose.pose.position.y,o.pose.pose.position.z=map(float,position)
            o.pose.pose.orientation.x,o.pose.pose.orientation.y,o.pose.pose.orientation.z,o.pose.pose.orientation.w=map(float,quat)
            o.twist.twist.linear.x,o.twist.twist.linear.y,o.twist.twist.linear.z=map(float,linear)
            o.twist.twist.angular.x,o.twist.twist.angular.y,o.twist.twist.angular.z=map(float,angular)
            return o
        self.base_pub.publish(odom('reuse/base',s['position'],s['quat_xyzw'],s['body_linear'],s['body_angular']))
        yaw=s['yaw'];heading=(0.,0.,math.sin(yaw/2),math.cos(yaw/2))
        self.nav_pub.publish(odom('reuse/nav_base',(*s['position'][:2],0.),heading,s['nav_linear'],(0.,0.,s['nav_yaw_rate'])))
        j=JointState();set_stamp(j.header.stamp,value);j.header.frame_id='reuse/base';j.name=list(JOINT_NAMES);j.position=list(s['joint_positions']);j.velocity=list(s['joint_velocities']);self.joint_pub.publish(j)
        def tf(parent,child,position,quat):
            t=TransformStamped();set_stamp(t.header.stamp,value);t.header.frame_id=parent;t.child_frame_id=child
            t.transform.translation.x,t.transform.translation.y,t.transform.translation.z=map(float,position)
            t.transform.rotation.x,t.transform.rotation.y,t.transform.rotation.z,t.transform.rotation.w=map(float,quat)
            return t
        transforms=[tf('reuse/odom','reuse/nav_base',(*s['position'][:2],0.),heading),tf('reuse/nav_base','reuse/base',(0.,0.,s['position'][2]),s['residual_quat_xyzw'])]
        # Post-integration kinematics: do not stamp pre-step body transforms as new observations.
        p._ch13_mujoco.mj_kinematics(p.mjModel,p.mjData)
        for body in range(1,p.mjModel.nbody):
            parent=int(p.mjModel.body_parentid[body])
            if parent==0:continue
            rp=Rotation.from_quat(np.roll(p.mjData.xquat[parent],-1));rc=Rotation.from_quat(np.roll(p.mjData.xquat[body],-1))
            position=rp.inv().apply(p.mjData.xpos[body]-p.mjData.xpos[parent]);quat=(rp.inv()*rc).as_quat()
            transforms.append(tf('reuse/'+p.mjModel.body(parent).name,'reuse/'+p.mjModel.body(body).name,position,quat))
        if hasattr(p,'_ch13_sensors'):transforms.extend(p._ch13_sensors.transforms(tf))
        self.tf_pub.publish(TFMessage(transforms=transforms))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo-root',required=True);parser.add_argument('--max-sim-s',type=float,default=40.);parser.add_argument('--report',required=True);parser.add_argument('--scene',choices=['free','obstacle','blocked','vision']);args=parser.parse_args()
    root=Path(args.repo_root).resolve();report=Path(args.report);report.parent.mkdir(parents=True,exist_ok=True)
    S={'pid':os.getpid(),'ppid':os.getppid(),'result':'ERROR','normal_shutdown_requested':False};node=p=None;executor=None;rx=None;owned_threads=[];rows=[];last_window=[];sensors=None;scheduler=None
    import fcntl
    lockfile=(root.parent/'ch13_reuse_engine.lock').open('a+')
    try:
        fcntl.flock(lockfile,fcntl.LOCK_EX|fcntl.LOCK_NB);lockfile.seek(0);lockfile.truncate();lockfile.write(str(os.getpid()));lockfile.flush()
        lock=json.loads((root/'Ch13/dependencies/section_13_5_reuse.lock.json').read_text());up=root.parent/'upstream-iit-locomanipulation-d010212'
        assert all(hashlib.sha256((up/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in lock['files']),'upstream asset hash mismatch'
        from ament_index_python.packages import get_package_share_directory
        helper=Path(get_package_share_directory('ch13_navigation_reuse'))/'upstream_corrections/reproduce_upstream.py'
        assert hashlib.sha256(helper.read_bytes()).hexdigest()==lock['corrected_deployment_profile']['source_helper_sha256'],'installed correction hash mismatch'
        spec=importlib.util.spec_from_file_location('ch13_pinned_corrections',helper);correction=importlib.util.module_from_spec(spec);spec.loader.exec_module(correction)
        sys.path.insert(0,str(up/'deploy'));import play_mujoco as upstream
        import locomotion_policy_wrapper as policy_module
        from .cpu_policy import cpu_session
        policy_module.ort=types.SimpleNamespace(InferenceSession=cpu_session)
        import torch;torch.set_num_threads(1)
        if args.scene:
            import mujoco as real_mujoco
            from .scene import make_model
            from .sensors import HeadlessViewer,SensorSuite
            class ModelLoader:
                @staticmethod
                def from_xml_path(path):return make_model(path,args.scene)
            class MujocoProxy:
                MjModel=ModelLoader
                viewer=types.SimpleNamespace(launch_passive=lambda *a,**kw:HeadlessViewer())
                def __getattr__(self,name):return getattr(real_mujoco,name)
            upstream.mujoco=MujocoProxy()
        closed=threading.Event();saved_input=builtins.input
        def close_console(*a):closed.set();return 'closeConsole'
        threads_before=set(threading.enumerate());builtins.input=close_console
        try:p=upstream.PlayMujoco();assert closed.wait(1.),'console did not close'
        finally:builtins.input=saved_input
        owned_threads=[t for t in threading.enumerate() if t not in threads_before]
        correction.freeze_arm_reference(p);caps=p.mjModel.actuator_ctrlrange.copy();correction.configure_native_arm_pd(p.mjModel,p.Kp_arm,p.Kd_arm)
        source=textwrap.dedent(inspect.getsource(upstream.PlayMujoco.run));source=correction.consistent_walking_run_source(source)
        from .scheduler import SteadyScheduler
        scheduler=SteadyScheduler(p.simulation_dt);p.last_render_time=scheduler.time()
        namespace=dict(upstream.PlayMujoco.run.__globals__);namespace['time']=scheduler;exec(compile(source,'ch13_pinned_run','exec'),namespace);p.run=types.MethodType(namespace['run'],p);p._ch13_mujoco=upstream.mujoco
        assert tuple(p.mjModel.joint(i).name for i in range(1,p.mjModel.njnt))==JOINT_NAMES
        if args.scene:sensors=SensorSuite(p.mjModel,p.mjData,args.scene,report.parent);p._ch13_sensors=sensors
        rclpy.init(args=[]);node=Platform();node.allow_tf_broadcasters=bool(args.scene)
        if sensors is not None:sensors.attach(node)
        executor=SingleThreadedExecutor();executor.add_node(node);rx_error=[]
        def spin():
            try:executor.spin()
            except BaseException:rx_error.append(traceback.format_exc());node.guard.trip('RX_FAILED')
        rx=threading.Thread(target=spin,name='reuse_ros_rx');rx.start()
        original_viewer=p.viewer;original_step=upstream.mujoco.mj_step;start=time.monotonic();step_count=0;last_decision=None;max_ratio=0.;timing=[];previous_exit=time.monotonic();previous_cpu=time.thread_time()
        class Viewer:
            def __getattr__(self,name):return getattr(original_viewer,name)
            def is_running(self):return not node.stop_requested and p.mjData.time<args.max_sim_s and original_viewer.is_running()
        p.viewer=Viewer()
        def step(model,data,*a,**kw):
            nonlocal step_count,last_decision,max_ratio,previous_exit,previous_cpu
            begin=time.monotonic();cpu_begin=time.thread_time()
            def record(stage,wall,cpu):
                span=time.monotonic()-wall
                if span>.1 and len(timing)<50:timing.append({'stage':stage,'sim_s':float(data.time),'wall_s':span,'thread_cpu_s':time.thread_time()-cpu})
            record('upstream_loop',previous_exit,previous_cpu)
            sim_ns=max(1,round(data.time*1e9));d,arm=node.engine_command(sim_ns);last_decision=d
            record('engine_command_lock',begin,cpu_begin);marker=time.monotonic();cpu_marker=time.thread_time()
            p.ref_base_lin_vel_H[:]=[d.vx,0.,0.];p.ref_base_ang_yaw_dot=d.wz;p.desired_joint_pos_arm[0]=arm
            data.ctrl[12:18]=p.desired_joint_pos_arm
            original_step(model,data,*a,**kw);record('physics',marker,cpu_marker);marker=time.monotonic();cpu_marker=time.thread_time();step_count+=1;wall=time.monotonic()
            ratio=float(np.max(abs(data.actuator_force)/caps[:,1]));max_ratio=max(max_ratio,ratio)
            if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all() or not np.isfinite(ratio) or ratio>1+1e-8:raise RuntimeError('nonfinite state or original actuator cap violation')
            q,v,state,tilt=node.capture(p,round(data.time*1e9),wall,d)
            if q[2]<.12 or tilt>math.pi/4:raise RuntimeError('fall bound')
            if sensors is not None:
                for contact in data.contact:
                    a,b=map(int,contact.geom)
                    if (model.geom_group[a]==5 and model.geom_bodyid[b]>0) or (model.geom_group[b]==5 and model.geom_bodyid[a]>0):raise RuntimeError('robot/environment obstacle collision')
                sensors.step(p,state)
            record('capture_sensor',marker,cpu_marker);marker=time.monotonic();cpu_marker=time.thread_time()
            row={'sim_s':float(data.time),'wall':wall,'qpos':q.tolist(),'qvel':v.tolist(),'vx':d.vx,'wz':d.wz,'mode':d.mode,'fault':d.fault,'arm_target':p.desired_joint_pos_arm.copy().tolist()}
            last_window.append(row)
            if len(last_window)>1200:del last_window[:200]
            if step_count%10==0:rows.append(row);node.publish_state(p,state)
            record('state_publish',marker,cpu_marker);previous_exit=time.monotonic();previous_cpu=time.thread_time()
        upstream.mujoco.mj_step=step
        try:p.run()
        finally:upstream.mujoco.mj_step=original_step
        S.update(step_outliers=timing,result='COMPLETED',normal_shutdown_requested=node.stop_requested,sim_s=float(p.mjData.time),wall_s=time.monotonic()-start,physics_steps=step_count,max_force_cap_ratio=max_ratio,final_mode=node.guard.mode,final_fault=node.guard.fault,arm_events=node.events,rx_error=rx_error,actual_pose=p.mjData.qpos[:7].tolist())
        if not node.stop_requested or rx_error:raise RuntimeError('unrequested engine end or ROS receiver failure')
    except BaseException:S['error']=traceback.format_exc();S['result']='ERROR'
    finally:
        if scheduler is not None:S['scheduler']=scheduler.summary()
        if sensors is not None:
            S['camera_worker_joined']=sensors.close()
            if not S['camera_worker_joined']:S['result']='ERROR';S['camera_error']='renderer worker failed to join'
        if p is not None:p.viewer.close()
        if executor is not None:executor.shutdown(timeout_sec=2.)
        if rx is not None:rx.join(2.)
        S['rx_joined']=rx is None or not rx.is_alive()
        for t in owned_threads:t.join(2.)
        S['upstream_threads_joined']=all(not t.is_alive() for t in owned_threads)
        if node is not None:node.destroy_node();rclpy.try_shutdown()
        lockfile.close()
        (report.parent/'engine_observations.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
        (report.parent/'last_stop_500hz.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in last_window))
        report.write_text(json.dumps(S,indent=2)+'\n');print(json.dumps(S,indent=2),flush=True)
    if S['result']!='COMPLETED' or not S['rx_joined'] or not S['upstream_threads_joined']:sys.exit(1)
if __name__=='__main__':main()
