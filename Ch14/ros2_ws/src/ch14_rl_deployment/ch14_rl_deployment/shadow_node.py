"""Read-only 50Hz ROS policy shadow. No joint target publishers or enable service."""
import json,time
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock,ClockType
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu,JointState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from .policy import OnnxPolicy
from .observation_adapter import ObservationAdapter
class Shadow(Node):
    def __init__(self):
        super().__init__("ch14_rl_shadow")
        for k in ("onnx_path","contract_path","contract_sha256"):self.declare_parameter(k,"")
        self.policy=OnnxPolicy(*[self.get_parameter(k).value for k in ("onnx_path","contract_path","contract_sha256")])
        self.adapter=ObservationAdapter(self.policy.contract)
        self.status=self.create_publisher(String,"/rl/controller_status",10);self.count=0;self.overruns=0
        for name,typ,topic in [("imu",Imu,"/imu/data_raw"),("joints",JointState,"/joint_states"),("velocity",Odometry,"/simulation/odom"),("command",Twist,"/cmd_vel")]:
            self.create_subscription(typ,topic,lambda m,n=name:self.adapter.receive(n,m,self.now()),10 if name=="command" else qos_profile_sensor_data)
        self.timer=self.create_timer(.02,self.tick);self.watch=self.create_timer(.05,self.watchdog,clock=Clock(clock_type=ClockType.STEADY_TIME))
    def now(self):return self.get_clock().now().nanoseconds/1e9
    def emit(self,status,obs=None,action=None,elapsed=0):
        self.status.publish(String(data=json.dumps(dict(status=status,enabled=False,policy_scope=self.policy.contract["policy_scope"],inferences=self.count,published=0,overruns=self.overruns,sim_time=self.now(),inference_seconds=elapsed,observation=None if obs is None else obs.tolist(),shadow_action=None if action is None else action.tolist(),faults=self.adapter.faults),allow_nan=False)))
    def watchdog(self):
        if any(time.monotonic()-self.adapter.wall.get(k,-float("inf"))>.5 for k in ("imu","joints","velocity")):self.emit("WALL_SENSOR_TIMEOUT")
    def tick(self):
        try:
            obs=self.adapter.observation(self.now());t=time.monotonic();action,_=self.policy.predict(obs);elapsed=time.monotonic()-t
            if elapsed>.02:self.overruns+=1;self.emit("INFERENCE_OVERRUN",elapsed=elapsed);return
            self.count+=1;self.emit("SHADOW",obs,action,elapsed)
        except (ValueError,RuntimeError) as e:self.emit(str(e))
def main(args=None):
    rclpy.init(args=args);n=None
    try:n=Shadow();rclpy.spin(n)
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:
        if n is not None:
            print(json.dumps(dict(status="CH14_SHADOW_SHUTDOWN",inferences=n.count,published=0,overruns=n.overruns)),flush=True);n.destroy_node()
        if rclpy.ok():rclpy.shutdown()
if __name__=="__main__":main()
