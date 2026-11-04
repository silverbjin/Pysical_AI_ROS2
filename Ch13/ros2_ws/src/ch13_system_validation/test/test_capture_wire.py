"""Actual DDS capture-health relay, no simulator and no fabricated receipt."""
import json
import subprocess
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from ament_index_python.packages import get_package_prefix
from ch13_navigation_reuse.wire import decode


def test_native_capture_channel_preserves_original_stamp_and_dds_receipt():
    relay=subprocess.Popen([get_package_prefix('ch13_reuse_wire')+'/lib/ch13_reuse_wire/ingress','--manipulation'],
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    rclpy.init(args=[]);node=Node('validation_capture_wire_fixture');packets=[]
    node.create_subscription(String,'/ch13/reuse/ingress/manipulation/manipulation_capture_health',lambda m:packets.append(m),1)
    publisher=node.create_publisher(String,'/ch13/reuse/vision/health',1)
    original=dict(capture_ns=1_000_000_000,capture_wall=time.monotonic(),scope='validated_RGBD_capture_and_past_TF')
    try:
        deadline=time.monotonic()+3.
        while not packets and time.monotonic()<deadline:
            publisher.publish(String(data=json.dumps(original)));rclpy.spin_once(node,timeout_sec=.02)
        assert packets,'native manipulation capture-health relay missing'
        key,message,info=decode(packets[-1].data)
        assert key=='manipulation_capture_health'
        assert json.loads(message.data)==original
        assert original['capture_wall']<=info['receipt_wall']<=time.monotonic()
        assert info['publisher_gid'] and info['relay_gid']
    finally:
        node.destroy_node();rclpy.try_shutdown();relay.terminate();relay.wait(timeout=3.)
