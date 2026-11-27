"""Independent actual DDS server; intentionally inject bounded test-only behavior."""
import json,time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer,GoalResponse,CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from ch15_interfaces.action import PickObject
from std_msgs.msg import String
from ch15_adapters.qos_profiles import profile
class Fixture(Node):
    def __init__(self):
        super().__init__('g03_action_fixture')
        self.pub=self.create_publisher(String,'/g03/witness',profile(20))
        self.server=ActionServer(self,PickObject,'/g03/action',execute_callback=self.execute,goal_callback=self.admit,cancel_callback=lambda _:CancelResponse.ACCEPT,callback_group=ReentrantCallbackGroup())
    def admit(self,g):
        if g.object_class=='reject':return GoalResponse.REJECT
        if g.object_class=='before_accept':time.sleep(.35)
        return GoalResponse.ACCEPT
    def execute(self,h):
        mode=h.request.object_class;start=time.monotonic()
        duration=2.55 if mode in ('unconfirmed','late') else .9 if mode in ('cancel','before_accept','timeout') else .12
        while rclpy.ok() and time.monotonic()-start<duration:
            if h.is_cancel_requested and mode not in ('unconfirmed','late'):
                h.canceled();return PickObject.Result(success=False,error_message='fixture canceled')
            time.sleep(.02)
        if mode in ('abort','unconfirmed','late'):
            # late terminal after the caller already latched; cannot promote success
            if h.is_cancel_requested:h.canceled()
            else:h.abort()
            return PickObject.Result(success=False,error_message='fixture terminal')
        self.pub.publish(String(data=bytes(h.goal_id.uuid).hex()));h.succeed();return PickObject.Result(success=True)
def main():
    rclpy.init();n=Fixture();ex=MultiThreadedExecutor(num_threads=4);ex.add_node(n)
    try:ex.spin()
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:ex.shutdown(timeout_sec=5.);n.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
