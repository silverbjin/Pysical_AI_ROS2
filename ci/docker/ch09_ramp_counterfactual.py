#!/usr/bin/env python3
"""CI-only counterfactual: 6s smooth interpolation to ORIGINAL stand_up goals.

Never install as textbook node or claim physical robot safety. Compare the
resulting posture to original direct-step command using the same Gazebo model.
"""
import math
import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64

legs=("fr","fl","rr","rl")
kinds=("hip","thigh","calf")
names=[f"{leg}_{kind}_joint" for leg in legs for kind in kinds]
target={n:{"hip":0.0,"thigh":-.6,"calf":1.2}[n.split("_")[1]]
        for n in names}
rclpy.init()
node=Node("ch09_ci_smooth_ramp_counterfactual")
initial=None
started=None
counter=0
def on_state(m):
    global initial,started
    if initial is not None:return
    d=dict(zip(m.name,m.position))
    if all(n in d and math.isfinite(d[n]) for n in names):
        initial={n:float(d[n]) for n in names}
        started=time.monotonic()
        node.get_logger().info("CH09_RAMP_INITIAL_FROM_MEASURED_JOINTS "+repr(initial))
node.create_subscription(JointState,"/joint_states",on_state,10)
pubs={n:node.create_publisher(
    Float64,f"/model/my_quadruped/joint/{n}/cmd_pos",10) for n in names}
def send():
    global counter
    if initial is None:return
    elapsed=time.monotonic()-started
    alpha=max(0.,min(1.,elapsed/6.0))
    alpha=alpha*alpha*(3-2*alpha)
    for name,pub in pubs.items():
        m=Float64()
        m.data=initial[name]+(target[name]-initial[name])*alpha
        pub.publish(m)
    counter+=1
    if counter==1:node.get_logger().info("CH09_RAMP_COMMANDS_STARTED_DURATION_6S")
    if counter==65:node.get_logger().info("CH09_RAMP_FINAL_ORIGINAL_GOALS_REACHED")
node.create_timer(.1,send)
try:rclpy.spin(node)
except KeyboardInterrupt:pass
finally:
    node.destroy_node()
    if rclpy.ok():rclpy.shutdown()
