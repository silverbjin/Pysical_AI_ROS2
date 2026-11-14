#!/usr/bin/env python3
"""G04B diagnostic ONLY: attach contact *sensors* to a generated test URDF.

No collision surface / joint / dynamics / GazeboSimSystem / controller /
friction / original file is changed. A new Contact sensor reports what
actually blocks each finger. Not a physical grasp success criterion.
"""
import json,sys
from pathlib import Path
from xml.etree import ElementTree as ET

urdf,receipt=map(Path,sys.argv[1:3])
original=urdf.read_text()
root=ET.fromstring(original)
assert root.tag=="robot"
for link,collision in (("finger1","finger1_collision"),("finger2","finger2_collision")):
    source=root.find(f"./link[@name='{link}']")
    assert source is not None and len(source.findall("collision"))==1
    assert root.find(f"./gazebo[@reference='{link}']") is None
    gz=ET.SubElement(root,"gazebo",{"reference":link})
    sensor=ET.SubElement(gz,"sensor",{
        "name":f"g04b_{link}_contacts","type":"contact"})
    ET.SubElement(sensor,"always_on").text="true"
    ET.SubElement(sensor,"update_rate").text="100"
    ET.SubElement(ET.SubElement(sensor,"contact"),"collision").text=collision
# Add before final robot close, so ALL previously accepted URDF bytes stay
# in their original order and the only difference is new contact sensors.
additional=ET.tostring(root,encoding="unicode")
# Serialize only two generated gazebo tags to preserve the exact original
# robot description (including comments and controller interfaces).
nodes=[x for x in root.findall("gazebo") if x.attrib.get("reference") in
       ("finger1","finger2")]
assert len(nodes)==2
insert="\n"+ "\n".join(ET.tostring(x,encoding="unicode") for x in nodes)+"\n"
assert original.rstrip().endswith("</robot>")
new=original.rsplit("</robot>",1)[0]+insert+"</robot>\n"
assert original.split("<ros2_control",1)[1].split("</ros2_control>",1)[0] == \
       new.split("<ros2_control",1)[1].split("</ros2_control>",1)[0]
urdf.write_text(new)
receipt.write_text(json.dumps({
  "scope":"G04B_DIAGNOSTIC_ONLY_TWO_GAZEBO_CONTACT_SENSORS",
  "original_robot_urdf_source_unchanged":True,
  "physics_collision_shapes_changed":False,
  "force_attach_or_teleport":False,
  "instrumented_links":["finger1","finger2"],
  "expected_collision_names":["finger1_collision","finger2_collision"],
  "contact_sensor_diagnosis":"NOT_RUN",
  "bilateral_grasp":"NOT_RUN","Ch10":"HOLD"
},indent=2)+"\n")
print("CH07_77_G04B_TWO_FINGER_CONTACT_DIAGNOSTIC_SENSORS_STATIC_PASS")
