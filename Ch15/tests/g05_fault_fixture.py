"""Actual DDS mock fixture only; G08 fault acceptance is separate."""
import sys
import rclpy
from rclpy.executors import MultiThreadedExecutor
from ch15_adapters.mock_servers import MockServers
mode=sys.argv.pop(1)
class Fixture(MockServers):
    def command(self,x):
        super().command(x)
        if mode=='F01' and x>0:self.scan_enabled=False
    def execute(self,h,kind,action):
        if mode=='F06' and kind=='pick':
            result=action.Result();result.success=False;result.error_message='G05 F06 recording fixture: injected pick abort'
            h.abort()
            with self.lock:self.active=False
            return result
        return super().execute(h,kind,action)
rclpy.init();n=Fixture();ex=MultiThreadedExecutor(num_threads=4);ex.add_node(n)
try:ex.spin()
except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
finally:ex.shutdown(timeout_sec=6.);n.destroy_node();rclpy.try_shutdown()
