"""Actual DDS original capture health on an isolated navigation lane."""
import json,os,subprocess,time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from ament_index_python.packages import get_package_prefix
from ch13_navigation_reuse.navigation_boundary import NavigationBoundary
from ch13_navigation_reuse.wire import decode


def test_navigation_capture_health_bypasses_mixed_queue_without_restamping():
    env=dict(os.environ,CH13_VALIDATION_PROFILE='carry_v1')
    relay=subprocess.Popen([get_package_prefix('ch13_reuse_wire')+'/lib/ch13_reuse_wire/ingress','--manipulation'],
        env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    rclpy.init(args=[]);node=Node('validation_nav_health_lane');boundary=None;legacy=[]
    try:
        boundary=NavigationBoundary(isolated_health=True)
        def mixed(message):
            key,_,_=decode(message.data)
            if key=='vision_health':legacy.append(message)
        node.create_subscription(String,'/ch13/reuse/ingress/navigation',mixed,16)
        publisher=node.create_publisher(String,'/ch13/reuse/vision/health',1)
        capture=time.monotonic()
        original=dict(capture_ns=1_000_000_000,capture_wall=capture,scope='validated_RGBD_capture_and_past_TF')
        deadline=time.monotonic()+3.
        while boundary.vision.sample is None and time.monotonic()<deadline:
            publisher.publish(String(data=json.dumps(original)))
            rclpy.spin_once(node,timeout_sec=.01);rclpy.spin_once(boundary,timeout_sec=.01)
        assert boundary.vision.sample==(1_000_000_000,capture)
        assert boundary.health_native_receipt>=capture
        assert boundary.health_processed_wall>=boundary.health_native_receipt
        assert not legacy,'isolated health must not be routed through the mixed FIFO'
    finally:
        if boundary is not None:boundary.destroy_node()
        node.destroy_node();rclpy.try_shutdown();relay.terminate();relay.wait(timeout=3.)
