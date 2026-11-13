#!/usr/bin/env python3
"""Ch06 installed-model contract: exact Xacro+SRDF+5 joints+1 fake control.

This is static model evidence, NOT motion planning or execution success.
"""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
import xacro

result_file=Path(sys.argv[1])
result_file.parent.mkdir(parents=True,exist_ok=True)
description=Path(get_package_share_directory("my_robot_description"))
config=Path(get_package_share_directory("my_robot_moveit_config"))
source=description/"urdf/my_robot.ros2_control_rviz.urdf.xacro"
srdf_path=config/"config/my_robot.srdf"
assert source.is_file() and srdf_path.is_file()
urdf=xacro.process_file(str(source)).toxml()
root=ET.fromstring(urdf)
semantic=ET.parse(srdf_path).getroot()
assert root.attrib["name"]=="my_robot"==semantic.attrib["name"]
control=root.findall("ros2_control")
assert len(control)==1, f"expected exactly 1 mock hardware component, got {len(control)}"
assert control[0].find("hardware/plugin").text=="mock_components/GenericSystem"
groups=semantic.findall("./group")
arm=[g for g in groups if g.attrib["name"]=="arm_group"]
assert len(arm)==1
named=[g for g in semantic.findall("group_state")
       if g.attrib.get("group")=="arm_group" and g.attrib.get("name")=="ready"]
assert len(named)==1
joints={j.attrib["name"]:j for j in root.findall("joint")}
required=["joint1","joint2","joint3","joint4","joint_wrist"]
assert all(n in joints for n in required)
for name in required:
    actual=[x for x in named[0].findall("joint") if x.attrib["name"]==name]
    assert len(actual)==1
    target=float(actual[0].attrib["value"])
    limits=joints[name].find("limit")
    assert limits is not None
    assert float(limits.attrib["lower"])<=target<=float(limits.attrib["upper"])
assert [j.attrib["name"] for j in control[0].findall("joint") if
        j.attrib["name"] in required]==required
c=config/"config/ros2_controllers.yaml"
assert c.is_file()
res={"status":"MODEL_CONTRACT_PASS","model":str(source),"srdf":str(srdf_path),
     "root":root.attrib["name"],"joint_names":required,
     "controller":control[0].attrib["name"],
     "ros2_control_count":len(control),
     "named_ready":{"joint3":1.5708},
     "execution":"NOT_RUN_IN_THIS_STEP"}
result_file.write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n")
print("CH06_MODEL_CONTRACT_PASS "+json.dumps(res),flush=True)
