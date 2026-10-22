"""Signal the actual entry point while a real worker is in flight (no engine)."""
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import textwrap
import time

import pytest


@pytest.mark.parametrize('kind', ['detector', 'fusion'])
@pytest.mark.parametrize('stage', ['worker', 'constructor'])
def test_sigint_during_active_worker_exits_cleanly(kind, stage):
    code = textwrap.dedent('''
        import time
        from copy import deepcopy
        import rclpy
        from rclpy.parameter import Parameter
        from rclpy.executors import SingleThreadedExecutor
        from test_rgbd_cache import images, info
        from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose
        class TaggedExecutor(SingleThreadedExecutor):
            def spin(self):
                print('MAIN_SPIN', flush=True)
                return super().spin()
            def spin_once(self, *args, **kwargs):
                if not getattr(self, 'marked', False):
                    print('MAIN_SPIN', flush=True)
                    self.marked = True
                return super().spin_once(*args, **kwargs)
        if KIND == 'detector':
            import integrated_robot_vision.object_detector as module
            Original = module.ObjectDetector
            class Injected(Original):
                def __init__(self):
                    super().__init__(parameter_overrides=[Parameter('backend', value='color_fixture')])
                    if STAGE == 'constructor':
                        print('CONSTRUCTOR_ACTIVE', flush=True)
                        time.sleep(.15)
                    original = self.backend.detect
                    def slow(image):
                        print('WORKER_INFLIGHT', flush=True)
                        time.sleep(.15)
                        return original(image)
                    self.backend.detect = slow
                    stamp = self.get_clock().now().nanoseconds/1e9
                    rgb, depth = images(stamp, stamp)
                    self.on_info(info(stamp))
                    self.on_rgb(rgb)
            module.ObjectDetector = Injected
        else:
            import integrated_robot_vision.vision_processor as module
            original = module.lookup_capture_point
            def slow(*args, **kwargs):
                print('WORKER_INFLIGHT', flush=True)
                time.sleep(.15)
                return original(*args, **kwargs)
            module.lookup_capture_point = slow
            Original = module.VisionProcessor
            class Injected(Original):
                def __init__(self):
                    super().__init__()
                    if STAGE == 'constructor':
                        print('CONSTRUCTOR_ACTIVE', flush=True)
                        time.sleep(.15)
                    stamp = self.get_clock().now().nanoseconds/1e9
                    rgb, depth = images(stamp, stamp)
                    self.on_info(info(stamp))
                    self.on_rgb(rgb)
                    self.on_depth(depth)
                    message = Detection2DArray(header=deepcopy(rgb.header))
                    detection = Detection2D()
                    detection.bbox.center.position.x = detection.bbox.center.position.y = 5.
                    detection.bbox.size_x = detection.bbox.size_y = 6.
                    hypothesis = ObjectHypothesisWithPose()
                    hypothesis.hypothesis.class_id, hypothesis.hypothesis.score = 'fixture_red', .9
                    detection.results = [hypothesis]
                    message.detections = [detection]
                    self.on_detections(message)
            module.VisionProcessor = Injected
        module.SingleThreadedExecutor = TaggedExecutor
        module.main()
    ''').replace('KIND', repr(kind)).replace('STAGE', repr(stage))
    environment = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path), ROS_DOMAIN_ID='155')
    process = subprocess.Popen([sys.executable, '-u', '-c', code], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, env=environment,
                               start_new_session=True)
    lines = []
    try:
        markers = ('CONSTRUCTOR_ACTIVE',) if stage == 'constructor' else ('MAIN_SPIN', 'WORKER_INFLIGHT')
        deadline = time.monotonic()+8.
        while time.monotonic() < deadline and not all(
                marker in ''.join(lines) for marker in markers):
            if select.select([process.stdout], [], [], .1)[0]:
                line = os.read(process.stdout.fileno(), 4096).decode('utf-8', errors='replace')
                if not line:
                    break
                lines.append(line)
        assert all(marker in ''.join(lines) for marker in markers), ''.join(lines)
        process.send_signal(signal.SIGINT)
        remainder, _ = process.communicate(timeout=5.)
        output = ''.join(lines)+remainder
        assert process.returncode == 0, output
        assert 'Traceback' not in output and 'exception was never retrieved' not in output
        assert 'RuntimeWarning' not in output
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=3.)
