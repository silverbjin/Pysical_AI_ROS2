"""Only a logical mock. Never launch with a real robot or Ch13."""
import math, threading, time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.clock import Clock,ClockType
from geometry_msgs.msg import Twist,TwistStamped,TransformStamped
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from tf2_ros import StaticTransformBroadcaster
from nav2_msgs.action import NavigateToPose
from ch15_interfaces.action import PickObject,PlaceObject
from ch15_interfaces.srv import SwitchGait
from ch15_interfaces.msg import ReadyState
from .contracts import valid_pose,valid_timeout
from .qos_profiles import profile,sensor_qos

class MockServers(Node):
    def __init__(self):
        super().__init__('ch15_mock_servers')
        self.group=ReentrantCallbackGroup(); self.lock=threading.Lock()
        self.active=False; self.ready=False; self.ready_at=0.; self.gait='stand'; self.held=False; self.arrived=False; self.placed=False; self.motion_samples=0
        self.scan_enabled=self.declare_parameter('publish_scan',True).value
        self.cmd=self.create_publisher(TwistStamped,'/ch15/cmd_vel_in',profile())
        self.scan=self.create_publisher(LaserScan,'/scan',sensor_qos)
        self.gait_pub=self.create_publisher(String,'/ch15/gait_state',profile(transient=True))
        self.witness=self.create_publisher(String,'/ch15/mock_witness',profile(10))
        self.create_subscription(ReadyState,'/ch15/ready',self.on_ready,profile(),callback_group=self.group)
        self.create_subscription(Twist,'/cmd_vel',self.on_motion,profile(),callback_group=self.group)
        self.create_service(SwitchGait,'/switch_gait',self.switch,callback_group=self.group)
        self.servers=[]
        for kind,action,name in [('nav',NavigateToPose,'/navigate_to_pose'),('pick',PickObject,'/pick_object'),('place',PlaceObject,'/place_object')]:
            self.servers.append(ActionServer(self,action,name,execute_callback=lambda h,k=kind,a=action:self.execute(h,k,a),goal_callback=lambda g,k=kind:self.admit(g,k),cancel_callback=lambda _:CancelResponse.ACCEPT,callback_group=self.group))
        self.tf=StaticTransformBroadcaster(self)
        if self.declare_parameter('publish_tf',True).value:
            tf=TransformStamped(); tf.header.stamp=self.get_clock().now().to_msg();tf.header.frame_id='map';tf.child_frame_id='base_link';tf.transform.rotation.w=1.;self.tf.sendTransform(tf)
        self.create_timer(.1,self.sample,clock=Clock(clock_type=ClockType.STEADY_TIME),callback_group=self.group)
    def on_ready(self,msg):
        with self.lock: self.ready=msg.ready;self.ready_at=time.monotonic()
    def ready_now(self): return self.ready and time.monotonic()-self.ready_at<=.3
    def on_motion(self,msg):
        with self.lock:
            if self.active and msg.linear.x>0.:self.motion_samples+=1
    def sample(self):
        if self.scan_enabled:
            s=LaserScan();s.header.stamp=self.get_clock().now().to_msg();s.header.frame_id='base_link';s.angle_min=-.5;s.angle_max=.5;s.angle_increment=.5;s.range_min=.05;s.range_max=5.;s.ranges=[2.,2.,2.];self.scan.publish(s)
        with self.lock:gait=self.gait
        self.gait_pub.publish(String(data=gait))
    def switch(self,req,res):
        with self.lock:
            res.success=req.gait_type in ('stand','crawl','trot') and not self.active
            if res.success:self.gait=req.gait_type
        res.message='accepted; observe gait_state' if res.success else 'invalid gait or active goal'
        return res
    def admit(self,g,kind):
        pose=g.pose if kind=='nav' else g.target_pose
        p=pose.pose.position;q=pose.pose.orientation
        valid=valid_pose(pose.header.frame_id,[p.x,p.y,p.z],[q.x,q.y,q.z,q.w])
        if kind!='nav':valid=valid and valid_timeout(g.timeout_sec)
        if kind=='pick':valid=valid and g.object_class=='red_cube'
        with self.lock:
            valid=valid and self.ready_now() and not self.active
            if kind=='pick':valid=valid and self.arrived and not self.held and self.gait=='stand'
            if kind=='place':valid=valid and self.held and self.gait=='stand'
            if not valid:return GoalResponse.REJECT
            self.active=True;self.motion_samples=0
            return GoalResponse.ACCEPT
    def command(self,x):
        m=TwistStamped();m.header.stamp=self.get_clock().now().to_msg();m.header.frame_id='base_link';m.twist.linear.x=float(x);self.cmd.publish(m)
    def execute(self,h,kind,action):
        start=time.monotonic(); result=action.Result()
        deadline=start+(5. if kind=='nav' else float(h.request.timeout_sec))
        success=False;reason='deadline'
        try:
            # A logical transition requires a real observed arbiter output (nav)
            # or the prior state predicates and explicit state mutation (pick/place).
            while rclpy.ok() and time.monotonic()<deadline:
                if h.is_cancel_requested:reason='canceled';break
                with self.lock:ready=self.ready_now();samples=self.motion_samples
                if not ready:reason='readiness lost';break
                fb=action.Feedback()
                if kind=='nav':
                    fb.distance_remaining=float(max(0,3-samples))*.1
                    self.command(.1)
                else:
                    fb.current_state='MOCK_'+kind.upper();fb.distance_remaining=0.
                h.publish_feedback(fb)
                if kind=='nav' and samples>=3:
                    with self.lock:self.arrived=True
                    success=True;break
                if kind!='nav':
                    # Feedback then a bounded cancellation opportunity, followed by logical witness.
                    time.sleep(.15)
                    if h.is_cancel_requested:reason='canceled';break
                    with self.lock:
                        if not self.ready_now():reason='readiness lost';break
                        if kind=='pick' and self.arrived and not self.held and self.gait=='stand':self.held=True;success=True
                        if kind=='place' and self.held and self.gait=='stand':self.held=False;self.placed=True;success=True
                    if not success:reason='state predicate failed'
                    break
                time.sleep(.05)
            if success:
                self.witness.publish(String(data='MOCK:'+kind+':logical_transition'))
                h.succeed()
            elif h.is_cancel_requested:h.canceled()
            else:h.abort()
            if kind=='nav':
                result.error_code=0 if success else 1;result.error_msg='' if success else reason
            else:
                result.success=success;result.error_message='' if success else reason;result.execution_time=float(time.monotonic()-start)
            return result
        finally:
            if kind=='nav':self.command(0.)
            with self.lock:self.active=False

def main():
    rclpy.init();node=MockServers();ex=MultiThreadedExecutor(num_threads=4);ex.add_node(node)
    try:ex.spin()
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:
        ex.shutdown(timeout_sec=6.);node.destroy_node();rclpy.try_shutdown()
