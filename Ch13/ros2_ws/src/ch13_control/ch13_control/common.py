"""Graceful single-threaded native ROS loop; no signal-time entity destruction."""
import signal
import threading
import math
import rclpy
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import JointState
from builtin_interfaces.msg import Time

def seconds(stamp): return stamp.sec+stamp.nanosec*1e-9
def base_tilt(q):return math.acos(max(-1.,min(1.,1-2*(q.x*q.x+q.y*q.y))))
def sole_publisher_id(endpoints,expected_node=None):
    # Jazzy callback metadata has timestamps/sequence numbers, not publisher GID.
    # Fail closed on discovery ambiguity; derive identity from the graph endpoint.
    if len(endpoints)!=1:raise ValueError('requires exactly one publisher endpoint')
    if expected_node is not None and endpoints[0].node_name!=expected_node:raise ValueError('unexpected command producer')
    return bytes(endpoints[0].endpoint_gid).hex()
def time_msg(value):
    sec=int(value)
    return Time(sec=sec,nanosec=min(999999999,int((value-sec)*1e9)))
def joint_message(names,positions,stamp):
    m=JointState();m.name=list(names);m.position=list(map(float,positions));m.header.stamp=stamp
    return m
def run(factory):
    stop=threading.Event()
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    previous={s:signal.signal(s,lambda *_:stop.set()) for s in (signal.SIGINT,signal.SIGTERM)}
    node=None
    try:
        node=factory()
        while rclpy.ok() and not stop.is_set(): rclpy.spin_once(node,timeout_sec=.1)
    finally:
        if node is not None: node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()
        for s,h in previous.items():signal.signal(s,h)
