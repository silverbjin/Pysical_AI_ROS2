"""Break: TF observer starts too late, overwrites evidence, or cannot exit cleanly."""
import json
from pathlib import Path
import signal
import subprocess
import time

from ament_index_python.packages import get_package_prefix
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from geometry_msgs.msg import TransformStamped
from tf2_msgs.msg import TFMessage


def test_actual_tf_observer_exclusive_output_and_normal_shutdown(tmp_path):
    executable = Path(get_package_prefix('integrated_robot_navigation_sensors'))/'lib/integrated_robot_navigation_sensors/tf_provenance'
    output = tmp_path/'authority.jsonl'
    process = subprocess.Popen([str(executable), str(output)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    context = Context()
    rclpy.init(context=context)
    node = rclpy.create_node('tf_provenance_process_peer', context=context)
    executor = SingleThreadedExecutor(context=context)
    executor.add_node(node)
    publisher = node.create_publisher(TFMessage, '/tf', 10)
    transform = TransformStamped(child_frame_id='process_test_base')
    transform.header.frame_id = 'odom'
    transform.header.stamp.sec = 42
    transform.transform.rotation.w = 1.
    try:
        deadline = time.monotonic()+8.
        rows = []
        while not rows and time.monotonic() < deadline:
            assert process.poll() is None, process.communicate(timeout=1.)
            publisher.publish(TFMessage(transforms=[transform]))
            executor.spin_once(timeout_sec=.02)
            if output.exists():
                lines = output.read_text().splitlines(keepends=True)
                rows = [json.loads(line) for line in lines if line.endswith('\n')]
        assert len(rows) == 1
        assert rows[0]['stamp_ns'] == 42_000_000_000
        assert rows[0]['parent'] == 'odom' and rows[0]['child'] == 'process_test_base'
        actual_gid = bytes(node.get_publishers_info_by_topic('/tf')[0].endpoint_gid).hex()
        assert rows[0]['gid'] == actual_gid
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=5.)
        assert process.returncode == 0, (stdout, stderr)
        saved = output.read_bytes()
        rejected = subprocess.run([str(executable), str(output)], capture_output=True, timeout=5.)
        assert rejected.returncode != 0
        assert output.read_bytes() == saved
    finally:
        if process.poll() is None:
            process.terminate()
            process.communicate(timeout=5.)  # failure cleanup, never a normal-exit PASS
        executor.shutdown(timeout_sec=2.)
        node.destroy_node()
        context.try_shutdown()
