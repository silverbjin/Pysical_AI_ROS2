"""Serial receiver only; real DDS, no engine/motor acceptance."""
import threading
import time
import pytest
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from std_msgs.msg import UInt64
from integrated_robot_navigation.ingress_dispatch import IngressDispatch


@pytest.mark.parametrize('g2',[False,True])
@pytest.mark.parametrize('engine',['mujoco','gazebo'])
def test_explicit_gazebo_or_mujoco_g2_uses_serial_event_ingress(tmp_path,nav_robot_model,g2,engine):
    from test_execution_admission_contract import fixture
    from test_g2_control_cadence_ros import controller
    profile,expected=fixture(tmp_path,nav_robot_model,engine)
    ctx=Context();rclpy.init(context=ctx)
    node=controller(ctx,nav_robot_model,profile,expected,g2=g2,engine=engine)
    try:
        snapshot=node.ingress_worker.snapshot()
        assert snapshot['dispatch']==('owned_serial_events' if g2 or engine=='gazebo' else 'owned_serial_waitset')
        assert node.machine is None and not node.active and node.command_publication_count==0
        assert snapshot['clock_subscriptions']==['/navigation/control_clock']
    finally:
        node.destroy_node();ctx.try_shutdown()
    assert node.ingress_worker.joined and not node.ingress_worker.thread.is_alive()


@pytest.mark.parametrize('backend',['waitset','events'])
def test_serial_receiver_keeps_message_info_and_original_callback_thread(backend):
    ctx=Context();rclpy.init(context=ctx);peer=Node('event_ingress_peer',context=ctx)
    rows=[]
    def receive(msg,info):
        field=lambda name:info[name] if isinstance(info,dict) else getattr(info,name)
        rows.append((msg.data,field('source_timestamp'),field('received_timestamp'),threading.get_native_id()))
    worker=IngressDispatch(ctx,'event_ingress','/',[((UInt64,'/event_ingress/data',receive,5),{})],autostart=False)
    pub=peer.create_publisher(UInt64,'/event_ingress/data',5)
    try:
        worker.select_backend(backend);worker.start()
        deadline=time.monotonic()+2.
        while pub.get_subscription_count()!=1 and time.monotonic()<deadline:time.sleep(.005)
        assert pub.get_subscription_count()==1
        for value in range(6):
            pub.publish(UInt64(data=value));time.sleep(.01)
        deadline=time.monotonic()+.2
        while len(rows)<6 and worker.error is None and time.monotonic()<deadline:time.sleep(.005)
        assert worker.error is None,worker.error
        assert [row[0] for row in rows]==list(range(6))
        assert all(row[1]>0 and row[2]>0 for row in rows)
        assert {row[3] for row in rows}=={worker.thread.native_id}
        with pytest.raises(RuntimeError,match='started|running'):worker.select_backend('waitset')
    finally:
        worker.close();peer.destroy_node();ctx.try_shutdown()
    assert worker.joined and not worker.thread.is_alive()


def test_events_receiver_exception_stays_failed_without_restart():
    ctx=Context();rclpy.init(context=ctx);peer=Node('event_failure_peer',context=ctx)
    def fail(msg):raise ValueError('event receiver original failure')
    worker=IngressDispatch(ctx,'event_failure','/',[((UInt64,'/event_ingress/fail',fail,5),{})],autostart=False)
    pub=peer.create_publisher(UInt64,'/event_ingress/fail',5)
    try:
        worker.select_backend('events');worker.start()
        deadline=time.monotonic()+2.
        while pub.get_subscription_count()!=1 and time.monotonic()<deadline:time.sleep(.005)
        pub.publish(UInt64(data=1));worker.thread.join(timeout=.5)
        assert not worker.thread.is_alive() and 'event receiver original failure' in worker.error
        original=worker.error;pub.publish(UInt64(data=2));time.sleep(.025)
        assert worker.error==original and not worker.thread.is_alive()
        with pytest.raises(RuntimeError,match='started|running'):worker.select_backend('events')
    finally:
        worker.close();peer.destroy_node();ctx.try_shutdown()
    assert worker.joined
