"""ROS-free callback/lifecycle regression tests for Ch01 §1.6.

These tests use a stub of rclpy, not a running ROS2 executor or DDS transport.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'robot_ws/src/my_robot_controller/my_robot_controller/simple_controller.py'


class Log:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(message)


class NodeStub:
    instances = []
    raise_on_construct = False

    def __init__(self, name):
        if self.raise_on_construct:
            raise RuntimeError('node construction failed')
        self.name = name
        self.log = Log()
        self.period = None
        self.callback = None
        self.destroyed = False
        self.instances.append(self)

    def get_logger(self):
        return self.log

    def create_timer(self, period, callback):
        self.period, self.callback = period, callback
        return object()

    def destroy_node(self):
        self.destroyed = True


class TestSimpleController(unittest.TestCase):
    def setUp(self):
        NodeStub.instances = []
        NodeStub.raise_on_construct = False
        self.events = []
        self.ready = False
        module = types.ModuleType('rclpy')
        sub = types.ModuleType('rclpy.node')
        sub.Node = NodeStub
        module.init = lambda args=None: self._init()
        module.spin = lambda node: self._spin(node)
        module.shutdown = lambda: self._shutdown()
        module.ok = lambda: self.ready
        self.mod = module
        self.patcher = patch.dict(sys.modules, {'rclpy': module, 'rclpy.node': sub})
        self.patcher.start()
        spec = importlib.util.spec_from_file_location('ch01_simple_controller_under_test', SOURCE)
        self.target = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.target)

    def tearDown(self):
        self.patcher.stop()

    def _init(self):
        self.events.append('init')
        self.ready = True

    def _shutdown(self):
        self.events.append('shutdown')
        self.ready = False

    def _spin(self, node):
        self.events.append('spin')
        raise KeyboardInterrupt

    def test_name_and_heartbeat_interval(self):
        node = self.target.SimpleController()
        self.assertEqual(node.name, 'my_robot_node')
        self.assertEqual(node.period, 1.0)
        for _ in range(3):
            node.callback()
        self.assertEqual(node.counter, 3)
        self.assertTrue(node.log.messages[-1].endswith('(Heartbeat: 3)'))

    def test_shutdown_on_keyboard_interrupt(self):
        self.target.main()
        self.assertEqual(self.events, ['init', 'spin', 'shutdown'])
        self.assertTrue(NodeStub.instances[-1].destroyed)

    def test_cleanup_on_constructor_failure(self):
        NodeStub.raise_on_construct = True
        with self.assertRaisesRegex(RuntimeError, 'node construction failed'):
            self.target.main()
        self.assertEqual(self.events, ['init', 'shutdown'])

    def test_already_shutdown_context(self):
        def stop_context(node):
            self.events.append('spin')
            self.ready = False
        self.mod.spin = stop_context
        self.target.main()
        self.assertEqual(self.events, ['init', 'spin'])
        self.assertTrue(NodeStub.instances[-1].destroyed)


if __name__ == '__main__':
    unittest.main()
