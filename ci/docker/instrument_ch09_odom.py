#!/usr/bin/env python3
"""Add measurement-only Gazebo odometry to a generated Ch09 URDF for the CI trial.

Does not alter textbook Xacro, controllers, joints, collision shapes, or contact
physics. This is SIMULATION-ONLY instrumentation and is not a foot-contact test.
"""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

path=Path(sys.argv[1])
tree=ET.parse(path)
root=tree.getroot()
assert root.tag=="robot" and root.get("name")=="my_quadruped"
assert len(root.findall("./gazebo/plugin[@filename='gz-sim-odometry-publisher-system']"))==0
gz=ET.SubElement(root,"gazebo")
plug=ET.SubElement(gz,"plugin",{
    "filename":"gz-sim-odometry-publisher-system",
    "name":"gz::sim::systems::OdometryPublisher"})
for tag,value in [
    ("odom_frame","odom"),
    ("robot_base_frame","base_footprint"),
    ("odom_topic","/model/my_quadruped/odometry"),
    ("tf_topic","/model/my_quadruped/odometry_tf_ci_only"),
    ("dimensions","3"),
    ("odom_publish_frequency","30")]:
    ET.SubElement(plug,tag).text=value
tree.write(path,encoding="unicode",xml_declaration=True)
print("CH09_CI_ODOM_INSTRUMENTATION_PASS, controllers and collision unchanged",flush=True)
