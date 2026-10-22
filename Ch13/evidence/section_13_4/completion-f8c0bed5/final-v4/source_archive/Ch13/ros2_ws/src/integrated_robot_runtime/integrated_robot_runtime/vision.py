"""Bounded Image/Odometry pairing lab; this node does not infer objects or TF."""
import json
import queue
import threading
import time

import message_filters
from nav_msgs.msg import Odometry
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from .common import seconds, spin
from .policy import valid_pair


class VisionProcessor(Node):
    def __init__(self):
        super().__init__('vision_processor')
        self.declare_parameter('processing_delay_s', 0.2)
        self.delay = float(self.get_parameter('processing_delay_s').value)
        if not 0 <= self.delay <= 2:
            raise ValueError('processing_delay_s must be within [0, 2]')
        self.group = ReentrantCallbackGroup()
        self.pending = queue.Queue(maxsize=1)
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.accepted = self.rejected = self.dropped = 0
        self.publisher = self.create_publisher(String, '/architecture/synchronized', 10)
        self.diagnostics = self.create_publisher(String, '/architecture/vision', 10)
        self.image = message_filters.Subscriber(
            self, Image, '/architecture/image_raw', qos_profile=qos_profile_sensor_data,
            callback_group=self.group)
        self.odom = message_filters.Subscriber(
            self, Odometry, '/architecture/odom', qos_profile=qos_profile_sensor_data,
            callback_group=self.group)
        self.synchronizer = message_filters.ApproximateTimeSynchronizer(
            [self.image, self.odom], queue_size=10, slop=0.05)
        self.synchronizer.registerCallback(self.pair)
        self.worker = threading.Thread(target=self.process, name='bounded_vision_worker')
        self.worker.start()
        self.create_timer(0.2, self.report)

    def pair(self, image, odom):
        first, second = seconds(image.header.stamp), seconds(odom.header.stamp)
        now = self.get_clock().now().nanoseconds * 1e-9
        if (not image.header.frame_id or not odom.header.frame_id
                or not valid_pair(first, second, now)):
            with self.lock:
                self.rejected += 1
            return
        # ATS invokes this under its own lock: do no heavy work here.
        try:
            self.pending.put_nowait((first, second))
        except queue.Full:
            try:
                self.pending.get_nowait()
            except queue.Empty:
                pass
            with self.lock:
                self.dropped += 1
            self.pending.put_nowait((first, second))

    def process(self):
        while not self.stop.is_set():
            try:
                first, second = self.pending.get(timeout=0.1)
            except queue.Empty:
                continue
            if self.stop.wait(self.delay):
                break
            now = self.get_clock().now().nanoseconds * 1e-9
            if not valid_pair(first, second, now):
                with self.lock:
                    self.rejected += 1
                continue
            with self.lock:
                self.accepted += 1
            self.publisher.publish(String(data=json.dumps({
                'image_stamp': first, 'odom_stamp': second, 'skew_s': first-second,
                'processing_delay_s': self.delay,
                'meaning': 'paired timestamps only; no interpolation or detection',
            })))

    def report(self):
        with self.lock:
            self.diagnostics.publish(String(data=json.dumps({
                'accepted': self.accepted, 'rejected': self.rejected,
                'dropped': self.dropped, 'pending_capacity': 1,
            })))

    def destroy_node(self):
        self.stop.set()
        self.worker.join(timeout=3)
        return super().destroy_node()


def main():
    spin(VisionProcessor, threads=2)
