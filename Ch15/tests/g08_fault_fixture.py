"""Faults triggered by actual DDS mission state/events; no motion outside original mock."""
import sys,json,time
from pathlib import Path
import rclpy
from rclpy.executors import MultiThreadedExecutor
from ch15_adapters.mock_servers import MockServers
from ch15_interfaces.msg import MissionEvent,TargetObservation
from ch15_adapters.qos_profiles import profile
mode=sys.argv.pop(1);out=Path(sys.argv.pop(1));trace=[]
assert mode in ('F03_transient','F03_persistent','F04','F06','F01')
def row(kind,**fields):trace.append(dict(kind=kind,wall_ns=time.monotonic_ns(),**fields))
class Fixture(MockServers):
    def __init__(self):
        super().__init__()
        assert not self.scan_enabled and not self.target_enabled
        self.destroy_publisher(self.scan)
        self.detect_attempt=0
        self.create_subscription(MissionEvent,'/ch15/mission_event',self.on_event,profile(100),callback_group=self.group)
    def on_event(self,m):
        if m.event=='RECOVERY_ATTEMPT':
            d=json.loads(m.detail)
            if d['step']=='detect':
                with self.lock:self.detect_attempt=d['attempt']
    def sample(self):
        super().sample()
        with self.lock:mission=self.mission;attempt=self.detect_attempt
        if mission is None or mission.state not in ('SEARCHING','APPROACHING','MANIPULATING'):return
        if mission.state=='SEARCHING' and (mode=='F03_persistent' or mode=='F03_transient' and attempt<2):
            row('target_withheld',attempt=attempt,state=mission.state)
            return
        t=TargetObservation();t.header.stamp=self.get_clock().now().to_msg();t.header.frame_id='map';t.mission_id=mission.mission_id;t.epoch=mission.epoch;t.source='MOCK';t.object_class='red_cube';t.valid=True;t.pose_kind='GRASP_POSE'
        if mode=='F04' and mission.state=='APPROACHING':
            t.epoch+=1;t.header.stamp.sec-=1
        t.target_pose.header=t.header;t.target_pose.pose.position.x=1.;t.target_pose.pose.position.z=.225;t.target_pose.pose.orientation.w=1.
        self.target.publish(t);row('target_published',state=mission.state,epoch=t.epoch,stamp_ns=t.header.stamp.sec*10**9+t.header.stamp.nanosec)
    def admit(self,g,kind):
        result=super().admit(g,kind);row('goal_admission',action=kind,result=result.name);return result
    def execute(self,h,kind,action):
        if mode=='F06' and kind=='pick':
            result=action.Result();result.success=False;result.error_message='G08 mock injected abort'
            row('pick_fault',uuid=bytes(h.goal_id.uuid).hex(),success=False)
            with self.lock:self.active=False
            h.abort();return result
        return super().execute(h,kind,action)
rclpy.init();n=Fixture();ex=MultiThreadedExecutor(num_threads=4);ex.add_node(n)
try:ex.spin()
except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
finally:
    ex.shutdown(timeout_sec=6);n.destroy_node();rclpy.try_shutdown()
    out.write_text(json.dumps(trace,indent=2)+'\n')
