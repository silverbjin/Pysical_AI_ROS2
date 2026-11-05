"""Real local DDS wire tests; no MuJoCo engine."""
import importlib.util,sys,time,threading,json,unittest,subprocess,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROS=importlib.util.find_spec('rclpy') is not None
if ROS:
    import rclpy
    from rclpy.context import Context
    from rclpy.node import Node
    from rclpy.executors import SingleThreadedExecutor
    from geometry_msgs.msg import TwistStamped
    from builtin_interfaces.msg import Time
    from rosgraph_msgs.msg import Clock
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import JointState
    from std_srvs.srv import Trigger
    from std_msgs.msg import String
    from ch13_navigation_reuse.command_gateway import CommandGateway
N='/ch13/reuse'
@unittest.skipUnless(ROS,'requires Jazzy local DDS')
class WireTests(unittest.TestCase):
    def setUp(self):
        self.relay=subprocess.Popen([__import__('ament_index_python.packages',fromlist=['get_package_prefix']).get_package_prefix('ch13_reuse_wire')+'/lib/ch13_reuse_wire/ingress'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        rclpy.init();self.g=CommandGateway();self.n=Node('reuse_wire_probe');self.outputs=[];self.status={};self.ns=2_000_000_000;self.raw=True;self.rollback=False;self.paused=False;self.base_enabled=True;self.joints_enabled=True;self.future_base=False
        self.clock=self.n.create_publisher(Clock,'/clock',1);self.base=self.n.create_publisher(Odometry,N+'/engine_state',1);self.joints=self.n.create_publisher(JointState,N+'/joint_states',1);self.cmd=self.n.create_publisher(TwistStamped,N+'/cmd_vel_raw',1)
        self.n.create_subscription(TwistStamped,N+'/cmd_vel_safe',lambda x:self.outputs.append(x),10)
        self.n.create_subscription(String,N+'/gateway/status',lambda x:setattr(self,'status',json.loads(x.data)),10)
        self.source_ready=False
        self.timer=self.n.create_timer(.02,self.send,clock=__import__('rclpy.clock',fromlist=['Clock']).Clock(clock_type=__import__('rclpy.clock_type',fromlist=['ClockType']).ClockType.STEADY_TIME))
        self.ex=SingleThreadedExecutor();self.ex.add_node(self.g);self.ex.add_node(self.n);self.t=threading.Thread(target=self.ex.spin);self.t.start()
    def send(self):
        if not self.source_ready:
            # Do not advance the synthetic clock while the relay is still
            # constructing/discovering its separate clock/state subscriptions.
            # Once admitted, loss/replacement tests retain their original flow.
            self.source_ready=(self.clock.get_subscription_count()==2
                and self.base.get_subscription_count()==1
                and self.joints.get_subscription_count()==1
                and self.cmd.get_subscription_count()==1
                and self.g.count_publishers(N+'/ingress/gateway')==1)
            if not self.source_ready:return
        if not self.paused:self.ns+=20_000_000
        stamp_ns=self.ns-(1_000_000_000 if self.rollback else 0)
        c=Clock();c.clock.sec=stamp_ns//1_000_000_000;c.clock.nanosec=stamp_ns%1_000_000_000;self.clock.publish(c)
        o=Odometry();o.header.stamp=c.clock;o.header.frame_id='reuse/odom';o.child_frame_id='reuse/base';o.pose.pose.position.z=.3;o.pose.pose.orientation.w=1.
        if self.future_base:
            o.header.stamp=Time(sec=stamp_ns//1_000_000_000+1,nanosec=stamp_ns%1_000_000_000)
        if self.base_enabled:self.base.publish(o)
        j=JointState();j.header.stamp=c.clock;j.name=[f'{leg}_{joint}_joint' for leg in ['FL','FR','RL','RR'] for joint in ['hip','thigh','calf']]+[f'joint{i}' for i in range(1,9)];j.position=[0.]*20;j.velocity=[0.]*20;
        if self.joints_enabled:self.joints.publish(j)
        if self.raw:
            x=TwistStamped();raw_stamp=stamp_ns-getattr(self,'raw_delay_ns',0);x.header.stamp=Time(sec=raw_stamp//1_000_000_000,nanosec=raw_stamp%1_000_000_000);x.header.frame_id='reuse/nav_base';x.twist.linear.x=getattr(self,'vx',0.);self.cmd.publish(x)
    def until(self, predicate, timeout=2.):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if predicate():return True
            time.sleep(.01)
        return False
    def arm(self):
        client=self.n.create_client(Trigger,N+'/gateway/arm');self.assertTrue(client.wait_for_service(timeout_sec=2.))
        self.assertTrue(self.until(lambda:self.status.get('ready_for_arm'),timeout=3.),str(self.status));f=client.call_async(Trigger.Request());self.assertTrue(self.until(f.done));self.assertTrue(f.result().success,f.result().message)
    def test_live_raw_to_safe_requires_explicit_arm(self):
        self.assertTrue(self.until(lambda:len(self.outputs)>2));self.assertEqual(self.outputs[-1].twist.linear.x,0.)
        self.arm();self.vx=.15;self.assertTrue(self.until(lambda:self.outputs[-1].twist.linear.x>.05))
        self.assertLessEqual(self.outputs[-1].twist.linear.x,.2)
    def test_live_raw_loss_stops_and_latches(self):
        self.arm();self.vx=.15;self.assertTrue(self.until(lambda:self.outputs and self.outputs[-1].twist.linear.x>.05));self.raw=False
        self.assertTrue(self.until(lambda:self.status.get('mode')=='FAULT'));self.raw=True
        time.sleep(.15);self.assertEqual(self.outputs[-1].twist.linear.x,0.);self.assertEqual(self.status['mode'],'FAULT')
    def test_live_second_raw_publisher_faults(self):
        self.arm();extra=self.n.create_publisher(TwistStamped,N+'/cmd_vel_raw',1)
        self.assertTrue(self.until(lambda:self.status.get('mode')=='FAULT'));self.n.destroy_publisher(extra)
    def test_live_clock_rollback_faults(self):
        self.arm();self.rollback=True
        self.assertTrue(self.until(lambda:self.status.get('mode')=='FAULT'))
    def fault_stays_zero(self):
        self.assertTrue(self.until(lambda:self.status.get('mode')=='FAULT'),str(self.status))
        self.assertTrue(self.until(lambda:self.outputs and self.outputs[-1].twist.linear.x==0.))
        time.sleep(.12);self.assertEqual(self.status['mode'],'FAULT');self.assertEqual(self.outputs[-1].twist.linear.x,0.)
    def test_live_clock_pause_ignores_repeated_clock(self):
        self.arm();self.vx=.15;self.assertTrue(self.until(lambda:self.outputs[-1].twist.linear.x>.03));self.paused=True
        self.fault_stays_zero();self.paused=False;self.fault_stays_zero()
    def test_live_base_loss_latches_after_return(self):
        self.arm();self.base_enabled=False;self.fault_stays_zero();self.base_enabled=True;self.fault_stays_zero()
    def test_live_joint_loss_latches_after_return(self):
        self.arm();self.joints_enabled=False;self.fault_stays_zero();self.joints_enabled=True;self.fault_stays_zero()
    def test_live_future_state_faults(self):
        self.arm();self.future_base=True;self.fault_stays_zero();self.assertEqual(self.status['fault'],'FUTURE_SOURCE:base')
    def test_live_publisher_replacement_uses_actual_sample_gid(self):
        self.arm();old=self.status['source_receipts']['raw']['gid'];self.raw=False;self.n.destroy_publisher(self.cmd)
        self.cmd=self.n.create_publisher(TwistStamped,N+'/cmd_vel_raw',1);self.raw=True
        self.fault_stays_zero();self.assertEqual(self.status['fault'],'OWNER_REPLACED:raw',str(self.status));self.assertEqual(self.status['source_receipts']['raw']['gid'],old)
    def test_live_relay_loss_stops(self):
        self.arm();self.relay.terminate();self.relay.wait(timeout=3.);self.fault_stays_zero()
    def test_live_rearm_needs_reset_fresh_zero_and_explicit_arm(self):
        self.arm();self.raw=False;self.fault_stays_zero();self.raw=True;self.vx=0.
        client=self.n.create_client(Trigger,N+'/gateway/reset');self.assertTrue(client.wait_for_service(timeout_sec=2.));future=client.call_async(Trigger.Request());self.assertTrue(self.until(future.done));self.assertTrue(future.result().success)
        self.assertTrue(self.until(lambda:self.status.get('ready_for_arm')));self.assertEqual(self.status['mode'],'DISARMED');self.assertEqual(self.outputs[-1].twist.linear.x,0.)
        self.arm();self.vx=.1;self.assertTrue(self.until(lambda:self.outputs[-1].twist.linear.x>.03))
    def tearDown(self):
        self.ex.shutdown(timeout_sec=2.);self.t.join(2.);self.n.destroy_node();self.g.destroy_node();rclpy.shutdown();self.relay.terminate();self.relay.wait(timeout=3.);self.assertFalse(self.t.is_alive())
if __name__=='__main__':unittest.main()
