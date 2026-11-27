#!/usr/bin/env python3
"""Exercise the installed lifecycle during an active publish callback."""
import json
import os
import signal
import sys
from pathlib import Path
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from ch15_simulation.graceful_spin import run_node

mode, dest = sys.argv[1:]
assert mode in ("SIGINT", "SIGTERM", "exception")
events = []

class Probe(Node):
    def __init__(self):
        super().__init__("g09_detector_shutdown_probe")
        self.pub = self.create_publisher(String, "/ch15/g09/shutdown_probe", 10)
        self.timer = self.create_timer(0.01, self.tick)

    def tick(self):
        self.timer.cancel()
        events.append("callback_enter")
        if mode == "exception":
            raise ValueError("G09_EXPECTED_CALLBACK_ERROR")
        os.kill(os.getpid(), getattr(signal, mode))
        assert rclpy.ok(), "context invalidated inside active callback"
        events.append("context_valid_after_signal")
        self.pub.publish(String(data="publish_after_signal"))
        events.append("publish_after_signal")
        events.append("callback_complete")

    def destroy_node(self):
        assert rclpy.ok()
        events.append("destroy_node_before_context_shutdown")
        return super().destroy_node()

try:
    run_node(Probe)
except ValueError as exc:
    if mode != "exception" or str(exc) != "G09_EXPECTED_CALLBACK_ERROR":
        raise
    events.append("callback_error_propagated")
else:
    assert mode != "exception", "callback exception was swallowed"

assert not rclpy.ok(), "context still active after exit"
events.append("context_shutdown")
expected = (
    ["callback_enter", "destroy_node_before_context_shutdown",
     "callback_error_propagated", "context_shutdown"] if mode == "exception" else
    ["callback_enter", "context_valid_after_signal", "publish_after_signal",
     "callback_complete", "destroy_node_before_context_shutdown", "context_shutdown"]
)
assert events == expected, events
Path(dest).write_text(json.dumps({"result": "PASS", "mode": mode, "events": events}, indent=2) + "\n")
print("G09_DETECTOR_SHUTDOWN_PASS", mode)
