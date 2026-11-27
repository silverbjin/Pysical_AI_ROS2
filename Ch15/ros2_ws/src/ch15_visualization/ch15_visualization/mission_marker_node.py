"""Separate, observation-only RViz publishers. No action, command, or service client."""
import time
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from rclpy.qos import QoSProfile, ReliabilityPolicy
from visualization_msgs.msg import Marker
from ch15_interfaces.msg import MissionStatus, SafetyState, TargetObservation
from .marker_contract import Session, fresh, stamp_ns, valid_target, TARGET_NS, STATUS_NS
from .detection_marker_node import create_detection_marker, delete_marker

class MissionMarkerNode(Node):
    def __init__(self):
        super().__init__('ch15_mission_marker')
        self.mode=self.declare_parameter('mode','mock').value
        self.frame=self.declare_parameter('fixed_frame','map').value
        if not self.frame or self.frame.startswith('/'):
            raise ValueError('fixed_frame must be a nonempty TF frame')
        physical_id=self.declare_parameter('physical_mission_id','cube_lab').value
        self.session=Session(self.mode,physical_id)
        self.target_pub=self.create_publisher(Marker,'/ch15/visualization/target',10)
        self.status_pub=self.create_publisher(Marker,'/ch15/visualization/status',10)
        observation=QoSProfile(depth=10,reliability=ReliabilityPolicy.BEST_EFFORT)
        self.create_subscription(MissionStatus,'/ch15/mission_state',self.on_status,observation)
        self.create_subscription(SafetyState,'/ch15/safety_state',self.on_safety,observation)
        self.create_subscription(TargetObservation,'/ch15/target_observation',self.on_target,observation)
        self.terminal=False
        self.target_stamp=None
        self.target_at=None
        self.status_stamp=None
        self.status_at=None
        self.safety=None
        self.advance_at=time.monotonic()
        self.steady=Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(.05,self.tick,clock=self.steady)

    def now(self):
        n=self.get_clock().now()
        old=self.session.last_clock
        ok=self.session.clock(n.nanoseconds)
        if old is None or n.nanoseconds>old:
            self.advance_at=time.monotonic()
        if not ok or time.monotonic()-self.advance_at>.3:
            self.clear_target()
            self.clear_status()
            return None
        return n.nanoseconds

    def clear_target(self):
        if self.target_stamp is not None:
            for marker_id in (0,2):
                self.target_pub.publish(delete_marker(self.frame,self.get_clock().now().to_msg(),TARGET_NS,marker_id))
        self.target_stamp=self.target_at=None

    def clear_status(self):
        if self.status_stamp is not None:
            self.status_pub.publish(delete_marker(self.frame,self.get_clock().now().to_msg(),STATUS_NS,1))
        self.status_stamp=self.status_at=None
        self.safety=None

    def on_safety(self,msg):
        now=self.now()
        if now is not None and fresh(stamp_ns(msg.header.stamp),now):
            self.safety=(msg,time.monotonic())

    def on_status(self,msg):
        now=self.now()
        if now is None:
            return
        accepted,changed=self.session.status(msg,now)
        if not accepted:
            return
        if changed:
            self.clear_target()
            self.clear_status()
        self.terminal=msg.state in ('COMPLETED','ABORTED')
        self.status_stamp=stamp_ns(msg.header.stamp)
        self.status_at=time.monotonic()
        safety='UNKNOWN (not witnessed)'
        if self.safety and self.mode=='mock':
            s,t=self.safety
            if (s.epoch==msg.epoch and s.owner=='MOCK:ch15_command_arbiter'
                    and time.monotonic()-t<=.3 and fresh(stamp_ns(s.header.stamp),now)):
                safety='LATCHED' if s.latched else ('BLOCKED' if s.blocked else 'UNBLOCKED')
        m=Marker()
        # Status has no spatial pose: fixed display anchor, not a transformed observation.
        m.header.frame_id=self.frame
        m.header.stamp=msg.header.stamp
        m.ns=STATUS_NS
        m.id=1
        m.type=Marker.TEXT_VIEW_FACING
        m.action=Marker.ADD
        m.pose.position.z=1.2
        m.pose.orientation.w=1.0
        m.scale.z=.15
        m.color.r=m.color.g=m.color.b=m.color.a=1.
        m.lifetime.sec=1
        mode='REPLAY' if self.mode=='replay' else 'MOCK'
        m.text=f'{mode} | source={msg.source} | profile={msg.profile} | {msg.state} | safety={safety} | epoch={msg.epoch}'
        self.status_pub.publish(m)
        if msg.state in ('COMPLETED','ABORTED'):
            self.clear_target()

    def on_target(self,msg):
        now=self.now()
        if now is None or self.mode=='replay':
            return
        if self.mode=='mock' and (self.terminal or self.status_at is None or time.monotonic()-self.status_at>.3):
            self.clear_target()
            return
        if not valid_target(msg,self.frame,self.session.identity,self.mode,now):
            self.clear_target()
            return
        marker=create_detection_marker(msg.target_pose,0,msg.object_class,msg.source)
        self.target_pub.publish(marker)
        # Sphere text is not rendered by RViz; a separate label uses fixed, disjoint ID.
        label=create_detection_marker(msg.target_pose,2,msg.object_class,msg.source)
        label.type=Marker.TEXT_VIEW_FACING
        label.pose.position.z+=.12
        label.scale.z=.09
        label.text=f'{"PHYSICAL" if self.mode=="physical" else "MOCK"} | source={msg.source} | {msg.pose_kind}'
        self.target_pub.publish(label)
        self.target_stamp=stamp_ns(msg.target_pose.header.stamp)
        self.target_at=time.monotonic()

    def tick(self):
        now=self.now()
        if now is None:
            return
        t=time.monotonic()
        if self.target_stamp is not None and (not fresh(self.target_stamp,now) or t-self.target_at>.3):
            self.clear_target()
        if self.status_stamp is not None and (not fresh(self.status_stamp,now) or t-self.status_at>.3):
            self.clear_status()
            self.clear_target()

def main():
    rclpy.init()
    n=None
    try:
        n=MissionMarkerNode()
        rclpy.spin(n)
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):
        pass
    finally:
        if n is not None:
            n.destroy_node()
        rclpy.try_shutdown()
