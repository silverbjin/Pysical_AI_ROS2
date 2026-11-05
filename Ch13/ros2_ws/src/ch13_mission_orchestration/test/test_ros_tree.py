"""Installed API characterization: custom paced ticks preserve ROS snapshots."""
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rclpy.parameter import Parameter
import py_trees_ros
from ch13_mission_orchestration.tasks import TaskPort
from ch13_mission_orchestration.tree import Mission


def test_external_context_tree_setup_tick_and_snapshot_exchange():
    context=Context();rclpy.init(context=context)
    node=Node('ch13_bt_api_test',context=context,
        parameter_overrides=[Parameter('default_snapshot_stream',value=True)])
    mission=Mission(TaskPort())
    tree=py_trees_ros.trees.BehaviourTree(mission.root)
    try:
        tree.setup(node=node,timeout=5.)
        mission.tick(tree)
        assert tree.count==1
        assert node.count_publishers('/ch13_bt_api_test/snapshots')==1
        assert mission.port.snapshot()['requested']==['navigate']
    finally:
        tree.shutdown(destroy_node=False);node.destroy_node();context.try_shutdown()
