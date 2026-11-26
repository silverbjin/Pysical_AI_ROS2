"""Independent real DDS sensor replay and fault witness; no actuator publishers."""
import argparse,json,os,signal,subprocess,time
from pathlib import Path
import numpy as np,rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu,JointState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
from builtin_interfaces.msg import Time
from ament_index_python.packages import get_package_prefix
from ch14_rl_deployment.policy import OnnxPolicy,digest
class Probe(Node):
    def __init__(self,record,names):
        super().__init__("ch14_g07_witness");self.rec=record;self.names=names;self.t=1_000_000_000;self.rows=[]
        self.clock=self.create_publisher(Clock,"/clock",10)
        self.imu=self.create_publisher(Imu,"/imu/data_raw",qos_profile_sensor_data)
        self.joints=self.create_publisher(JointState,"/joint_states",qos_profile_sensor_data)
        self.odom=self.create_publisher(Odometry,"/simulation/odom",qos_profile_sensor_data)
        self.cmd=self.create_publisher(Twist,"/cmd_vel",10)
        self.create_subscription(String,"/rl/controller_status",lambda m:self.rows.append(json.loads(m.data)),10)
    def spin(self,seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:rclpy.spin_once(self,timeout_sec=.003)
    def stamp(self,n=None):
        n=self.t if n is None else n;return Time(sec=n//10**9,nanosec=n%10**9)
    def send(self,kind="valid",command=True):
        self.t+=20_000_000;self.clock.publish(Clock(clock=self.stamp()));self.spin(.006)
        if kind in ("stale","clock_only"):self.spin(.025);return
        r=self.rec;i=Imu();i.header.stamp=self.stamp(self.t-160_000_000 if kind=="skew" else self.t);i.header.frame_id="wrong" if kind=="frame" else "base_link"
        i.orientation.x,i.orientation.y,i.orientation.z,i.orientation.w=r["xyzw"] if kind!="quaternion" else [0.,0.,0.,0.]
        i.angular_velocity.x,i.angular_velocity.y,i.angular_velocity.z=r["angular"]
        j=JointState();j.header.stamp=self.stamp();j.header.frame_id="base_link"
        order=list(range(12))
        if kind=="shuffle":order=order[::-1]
        if kind=="missing":order=order[:-1]
        j.name=[self.names[k] for k in order];j.position=[r["positions"][k] for k in order];j.velocity=[r["velocities"][k] for k in order]
        if kind=="duplicate":j.name[-1]=j.name[0]
        if kind=="nan":j.velocity[0]=float("nan")
        o=Odometry();o.header.stamp=self.stamp();o.header.frame_id="odom";o.child_frame_id="base_link";o.pose.pose.position.z=r["height"]
        o.twist.twist.linear.x,o.twist.twist.linear.y,o.twist.twist.linear.z=r["linear"]
        c=Twist();c.linear.x,c.linear.y,c.angular.z=r["command"]
        if command:self.cmd.publish(c)
        self.imu.publish(i);self.joints.publish(j);self.odom.publish(o);self.spin(.025)
    def phase(self,kind,n=18,command=True):
        start=len(self.rows)
        for _ in range(n):self.send(kind,command)
        return self.rows[start:]
def main():
    p=argparse.ArgumentParser();p.add_argument("--export",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    cp=a.export/"policy_contract.json";onnx=a.export/"quadruped_policy.onnx";c=json.loads(cp.read_text());pol=OnnxPolicy(onnx,cp,digest(cp))
    records=json.loads((a.export/"sensor_replay.json").read_text());record=next(x for x in records[1:] if x["height"]>.2 and np.linalg.norm(x["xyzw"][:3])>.00001)
    expected=np.array(record["observation"],np.float32);expected[36:]=0
    exe=str(Path(get_package_prefix("ch14_rl_deployment"))/"lib/ch14_rl_deployment/rl_shadow")
    log=a.out/"shadow-node.log";handle=log.open("w")
    proc=subprocess.Popen([exe,"--ros-args","-p","use_sim_time:=true","-p","onnx_path:="+str(onnx),"-p","contract_path:="+str(cp),"-p","contract_sha256:="+digest(cp)],stdout=handle,stderr=subprocess.STDOUT,start_new_session=True,cwd="/tmp")
    rclpy.init();w=Probe(record,c["joint_names"]);result={"status":"FAIL","phases":{},"record":record}
    def check_valid(rows,cmd=True):
        hits=[x for x in rows if x["status"]=="SHADOW"]
        assert hits,"no actual SHADOW output"
        x=expected.copy()
        if not cmd:x[9:12]=0
        y,_=pol.predict(x)
        for row in hits[-5:]:
            np.testing.assert_allclose(row["observation"],x,atol=1e-5,rtol=1e-4)
            np.testing.assert_allclose(row["shadow_action"],y,atol=1e-5,rtol=1e-4)
            assert row["inference_seconds"]<=.02
        return len(hits)
    def fault(rows,pattern):
        bad=[i for i,x in enumerate(rows) if pattern in x["status"]]
        assert bad,(pattern,[x["status"] for x in rows])
        assert all(x["status"]!="SHADOW" for x in rows[bad[0]:]),(pattern,rows[bad[0]:])
        return len(bad)
    try:
        end=time.monotonic()+12
        while time.monotonic()<end:
            if proc.poll() is not None:raise RuntimeError("shadow startup failed")
            w.spin(.1)
            if w.imu.get_subscription_count() and w.joints.get_subscription_count() and w.odom.get_subscription_count() and w.cmd.get_subscription_count() and w.rows:break
        else:raise RuntimeError("DDS discovery timeout")
        for kind in ("valid","shuffle"):result["phases"][kind]=check_valid(w.phase(kind))
        for kind in ("missing","duplicate","nan","frame","quaternion"):
            result["phases"][kind]=fault(w.phase(kind),"INVALID_INPUT")
            result["phases"][kind+"_recovery"]=check_valid(w.phase("valid"))
        # Advance ROS clock without fresh sensors; stale guard then wall watchdog.
        rows=w.phase("stale",n=24);result["phases"]["stale"]=fault(rows,"Stale/future")
        result["phases"]["stale_recovery"]=check_valid(w.phase("valid"))
        # Separate skew injection: advance clock first so older IMU stamp is not out-of-order.
        w.phase("clock_only",n=12)
        result["phases"]["skew"]=fault(w.phase("skew"),"Sensor time skew")
        result["phases"]["skew_recovery"]=check_valid(w.phase("valid"))
        rows=w.phase("valid",n=40,command=False);result["phases"]["command_expired"]=check_valid(rows[-8:],False)
        start=len(w.rows);w.spin(.7);result["phases"]["wall_pause"]=fault(w.rows[start:],"WALL_SENSOR_TIMEOUT")
        result["phases"]["resume"]=check_valid(w.phase("valid"))
        # No command topic publisher from this node, even during faults.
        graph=w.get_topic_names_and_types();forbidden=[n for n,_ in graph if n=="/rl/joint_targets" or n.endswith("/cmd_pos") or n=="/joint_group_effort_controller/commands"]
        assert not any(w.count_publishers(n) for n in forbidden)
        assert all(x["published"]==0 and not x["enabled"] for x in w.rows)
        assert all(x["shadow_action"] is None for x in w.rows if x["status"]!="SHADOW")
        result.update(status="ROS_SHADOW_PASS",status_count=len(w.rows),shadow_count=sum(x["status"]=="SHADOW" for x in w.rows),command_publishers=0,command_emissions=0,max_inference_ms=max(x["inference_seconds"]*1000 for x in w.rows if x["status"]=="SHADOW"))
    finally:
        if proc.poll() is None:proc.send_signal(signal.SIGINT)
        try:rc=proc.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait();rc=-9
        handle.close();result["exit_code"]=rc
        (a.out/"shadow-result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
        (a.out/"shadow-dds.json").write_text(json.dumps(w.rows,indent=2,allow_nan=False)+"\n")
        w.destroy_node();rclpy.try_shutdown()
        assert rc==0 and "CH14_SHADOW_SHUTDOWN" in log.read_text()
if __name__=="__main__":main()
