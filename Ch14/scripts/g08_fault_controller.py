"""CI-only fault injection; never installed or used by learner launch."""
import time
import rclpy
from std_srvs.srv import Trigger
from ch14_rl_deployment.rl_controller import RLController
def main():
    rclpy.init();node=None
    try:
        node=RLController()
        original=node.model.predict
        armed=[False]
        def inject(request,response):
            armed[0]=True;response.success=True;response.message='one actual ONNX call delayed in test harness';return response
        def predict(*args,**kwargs):
            result=original(*args,**kwargs)
            if armed[0]:
                armed[0]=False
                time.sleep(.035)
            return result
        node.model.predict=predict
        node.create_service(Trigger,'/g08/test/overrun_once',inject)
        rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        if node is not None:node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
if __name__=='__main__':main()
