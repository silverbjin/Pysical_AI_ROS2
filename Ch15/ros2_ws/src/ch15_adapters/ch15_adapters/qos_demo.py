import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger
from .qos_profiles import profile,state_qos
class QosDemo(Node):
    def __init__(self):
        super().__init__('ch15_qos_demo');self.seq=0;self.active=False;self.used=False
        self.be=self.create_publisher(String,'/ch15/qos_demo/sensor',profile(10,reliable=False))
        self.state=self.create_publisher(String,'/ch15/mission_state_demo',state_qos)
        self.create_service(Trigger,'/ch15/qos_demo/start',self.start)
        self.create_timer(.1,self.tick)
    def start(self,req,res):
        res.success=not self.used and self.be.get_subscription_count()>=1
        if res.success:self.active=True;self.used=True
        res.message='one shot 10 samples';return res
    def tick(self):
        if not self.active:return
        self.seq+=1;self.be.publish(String(data=str(self.seq)));self.state.publish(String(data='S'+str(self.seq)))
        if self.seq==10:self.active=False
def main():
    rclpy.init();node=QosDemo()
    try:rclpy.spin(node)
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:node.destroy_node();rclpy.try_shutdown()
