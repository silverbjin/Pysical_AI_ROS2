#!/usr/bin/env python3
"""Check the Xacro-expanded URDF joint-name and limit contract."""
import sys
import xml.etree.ElementTree as ET

robot = ET.parse(sys.argv[1])
wanted = sys.argv[2:]
joints = {j.get("name"): j for j in robot.findall(".//joint")
          if j.get("type") in ("revolute", "continuous")}
missing = [name for name in wanted if name not in joints]
assert not missing, "Missing joints: " + str(missing)
for name in wanted:
    j = joints[name]
    assert j.find("parent") is not None, name + ": parent missing"
    assert j.find("child") is not None, name + ": child missing"
    assert j.find("axis") is not None, name + ": axis missing"
    limit = j.find("limit")
    assert limit is not None and float(limit.get("velocity", "0")) > 0, name + ": velocity limit invalid"
print("URDF_JOINT_CONTRACT_PASS count=" + str(len(wanted)) + " " + ",".join(wanted))
