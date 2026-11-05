"""Real renderer/DDS fixture only; no physics, joint publisher or picking claim."""
import threading,time,json
import mujoco
import pytest
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from ch13_navigation_reuse.camera_worker import CameraWorker
from ch13_navigation_reuse.command_gateway import N


@pytest.mark.parametrize('latest',[False,True])
def test_renderer_delivery_does_not_depend_on_blocked_parent_retention(latest,tmp_path):
    model=mujoco.MjModel.from_xml_string('''<mujoco><visual><global offwidth="320" offheight="240"/></visual>
      <worldbody><light pos="0 0 3"/><geom type="plane" size="2 2 .1"/>
      <camera name="reuse_rgbd" pos="0 0 1"/><body pos="0 0 .1"><joint type="slide"/>
      <geom type="sphere" size=".1" mass=".1"/></body></worldbody></mujoco>''')
    data=mujoco.MjData(model);entered=threading.Event();release=threading.Event();worker=None
    rclpy.init(args=[]);node=Node('renderer_delivery_fixture');seen=set();connected=threading.Event()
    def observe(message):
        stamp=message.header.stamp.sec*1_000_000_000+message.header.stamp.nanosec
        if stamp<1_000_000_000:connected.set()
        else:seen.add(stamp)
    subscription=node.create_subscription(Image,N+'/rgb',observe,8)
    def blocked_retention(rgb,depth,meta):
        if meta['capture_ns']>=1_000_000_000:entered.set();release.wait()
    try:
        worker=CameraWorker(model,data.qpos,blocked_retention,latest=latest,
                            capture_ledger=tmp_path/'captures.json' if latest else None)
        # A discovered writer does not prove the actual image path is ready.
        # Complete an end-to-end first-frame handshake before measurement.
        if latest:
            deadline=time.monotonic()+5.;stamp=500_000_000
            while not connected.is_set() and time.monotonic()<deadline:
                worker.offer(data.qpos,stamp,time.monotonic());stamp+=1_000_000
                rclpy.spin_once(node,timeout_sec=.01)
            assert connected.is_set(),'renderer DDS first-frame handshake deadline'
        deadline=time.monotonic()+2.
        while not entered.is_set() and time.monotonic()<deadline:
            worker.offer(data.qpos,1_000_000_000,time.monotonic());entered.wait(.01)
        assert entered.is_set(),'parent retention never received real renderer output'
        for index in range(3):
            worker.offer(data.qpos,2_000_000_000+index*100_000_000,time.monotonic())
            deadline=time.monotonic()+.15
            while time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.01)
        if latest:assert len(seen)>=2,'camera publication stalled behind parent retention'
        else:assert not seen,'legacy renderer must not acquire camera DDS ownership'
    finally:
        release.set()
        if worker is not None:assert worker.close()
        node.destroy_subscription(subscription);node.destroy_node();rclpy.try_shutdown()
    if latest:
        ledger=json.loads((tmp_path/'captures.json').read_text())
        assert ledger['publisher_closed'] and not ledger['error']
        assert len(ledger['captures'])>=len(seen)>=2
        assert len(worker.source_captures)==len(ledger['captures'])
        assert all(r['capture']['capture_wall']<=r['publish_started_wall']<=r['publish_finished_wall'] for r in ledger['captures'])
        for row in ledger['captures']:
            meta=row['capture']
            assert meta['capture_wall']<=meta['render_started_wall']<=meta['render_finished_wall']
            assert meta['capture_wall']<=meta['request_offer_wall']<=meta['render_started_wall']
            assert meta['request_to_render_wall_s']>=0
            assert meta['render_elapsed_cpu_s']>=0
