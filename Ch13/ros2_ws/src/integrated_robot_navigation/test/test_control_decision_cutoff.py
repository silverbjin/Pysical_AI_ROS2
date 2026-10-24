"""Concurrent ingress cannot change the meaning of a past control decision."""
from types import SimpleNamespace
import rclpy
from rclpy.context import Context
from integrated_robot_interfaces.msg import MotionState
from integrated_robot_navigation.crawl_controller import CrawlController
from integrated_robot_navigation.samples import Sample


def test_calibration_uses_the_tick_bundle_even_when_a_new_carry_arrives(monkeypatch):
    context = Context()
    rclpy.init(context=context)
    node = CrawlController(context=context)
    try:
        node.model = SimpleNamespace(model_sha256='model')
        monkeypatch.setattr(node,'count_publishers',lambda _:1)
        good = Sample(1_000_000_000,10_000_000_000,0,1,'base_link',
            dict(ready=True,generation=0,model_sha256='model'))
        node.inbox.receive('carry',good)
        bundle = node._bundle_snapshot(1_010_000_000)
        node.inbox.receive('carry',Sample(1_010_000_000,10_020_000_001,0,2,'base_link',good.data))
        valid,reason = node._calibration_carry(1_010_000_000,10_020_000_000)
        assert valid, 'a fresh prior sample was replaced by a future wall receipt: '+reason
        assert node._calibration_carry(1_010_000_000,10_020_000_000,bundle=bundle)[0]
        assert bundle.carry is good, 'a decision cannot reselect state midway through its checks'
    finally:
        node.destroy_node(); context.try_shutdown()


def test_guard_selection_uses_the_same_wall_cutoff_without_losing_late_candidate():
    context = Context()
    rclpy.init(context=context)
    node = CrawlController(context=context)
    try:
        old,new = MotionState(state='STAND'),MotionState(state='FAULT',fault_reason='new fault')
        old.header.stamp.sec=1
        new.header.stamp.sec,new.header.stamp.nanosec=1,10_000_000
        node._gate_pending={1_000_000_000:(old,10_000_000_000),
                            1_010_000_000:(new,10_020_000_001)}
        node._select_gate(1_010_000_000,wall_ns=10_020_000_000)
        assert node.gate is old
        assert 1_010_000_000 in node._gate_pending
        node._select_gate(1_010_000_000,wall_ns=10_020_000_001)
        assert node.gate is new and node.gate.fault_reason=='new fault'
        assert node.gate_receipt==10_020_000_001
    finally:
        node.destroy_node(); context.try_shutdown()
