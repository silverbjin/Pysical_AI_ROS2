"""Actual installed C++ ingress and DDS delivery into WorldMap, no engine."""
import json,os,subprocess,time
import rclpy
from std_msgs.msg import String
from ament_index_python.packages import get_package_prefix
from ch13_navigation_reuse.world_map import WorldMap


def test_native_status_dds_keeps_source_identity_and_updates_map(monkeypatch):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1')
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO','level3_house')
    monkeypatch.setenv('ROS_DOMAIN_ID','138')
    relay=subprocess.Popen([get_package_prefix('ch13_reuse_wire')+'/lib/ch13_reuse_wire/ingress','--manipulation'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    rclpy.init(domain_id=138);node=None
    try:
        node=WorldMap('vision');publisher=node.create_publisher(String,'/ch13/reuse/manipulation/status',1)
        original=list(node.map.data)
        row=dict(session='dds_episode',phase='CARRY_ARMED',task_phase='CARRY_ARMED',fault='',goal_id='outbound',transport_goal_id='reserved',transport_stage='ARMED',sequence=7,stamp_ns=1_000_000_000,capture_health_ns=990_000_000,gripper_target_contacts={'link7':.1,'link8':.1},gripper_force_hold={'ready':True})
        deadline=time.monotonic()+4.
        while not node.map_gate.removed and time.monotonic()<deadline:
            row['decision_wall']=time.monotonic();publisher.publish(String(data=json.dumps(row)))
            rclpy.spin_once(node,timeout_sec=.02)
        assert node.map_gate.removed,'native status relay did not reach map gate'
        sources=node.get_publishers_info_by_topic('/ch13/reuse/manipulation/status')
        assert len(sources)==1
        assert node.map_gate.event['source_gid']==bytes(sources[0].endpoint_gid).hex()
        assert node.map_gate.event['decision_wall']<=node.map_gate.event['receipt_wall']<=time.monotonic()
        assert list(node.map.data)!=original
    finally:
        if node is not None:node.destroy_node()
        rclpy.try_shutdown();relay.terminate();relay.wait(timeout=3.)