"""Exercise the installed bridge parser, not YAML spelling alone."""
from pathlib import Path
import signal
import subprocess
import time

import rclpy
from rclpy.qos import ReliabilityPolicy


def test_camera_bridge_creates_all_three_reliable_publishers(tmp_path):
    config = (Path(__file__).resolve().parents[2] / 'integrated_robot_description'
              / 'config/vision_bridge.yaml')
    topics = ('/camera/color/image_raw', '/camera/aligned_depth_to_color/image_raw',
              '/camera/color/camera_info')
    rclpy.init()
    node = rclpy.create_node('bridge_contract_observer')
    with (tmp_path / 'bridge.log').open('w+') as log:
        process = subprocess.Popen(
            ['ros2', 'run', 'ros_gz_bridge', 'parameter_bridge', '--ros-args',
             '-p', f'config_file:={config}', '-r', '__node:=bridge_contract'],
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 15
            endpoints = {}
            while time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=.1)
                endpoints = {topic: [entry for entry in node.get_publishers_info_by_topic(topic)
                                     if entry.node_name == 'bridge_contract'] for topic in topics}
                if all(endpoints.values()) or process.poll() is not None:
                    break
            log.flush()
            log.seek(0)
            assert all(endpoints.values()), log.read()
            assert all(entry.qos_profile.reliability == ReliabilityPolicy.RELIABLE
                       for entries in endpoints.values() for entry in entries)
        finally:
            if process.poll() is None:
                # Signal only the process group created above, including ros2's child.
                import os
                os.killpg(process.pid, signal.SIGINT)
                process.wait(timeout=10)
            node.destroy_node()
            rclpy.shutdown()
