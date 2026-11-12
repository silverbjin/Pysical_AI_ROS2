#!/usr/bin/env python3
"""Ch10 IK failure boundary: compare *actual* numerical solver with book URDF.

This does not patch geometry, simulate gait, or relabel an observed mismatch PASS.
"""
import importlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import sys

src = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2])
properties = ET.parse(src / "urdf/common/robot_properties.xacro").getroot()
def val(name):
    for item in properties.iter():
        if item.tag.endswith("property") and item.get("name") == name:
            return float(item.get("value"))
    raise ValueError("Xacro property missing: " + name)
sys.path.insert(0, str(src))
solver_type = importlib.import_module("my_quadruped_bot.inverse_kinematics").InverseKinematics
ik = solver_type()
urdf_thigh = val("thigh_length")
urdf_calf = val("calf_length")
# Numerical reachable-case: the URDF has 0.50m combined reach, while the
# actual solver may clamp this 0.45m sample as if the leg only had 0.40m reach.
target = (0.0, 0.05, -0.45)
angles = ik.solve(*target, is_right_leg=False)
reach_xacro = urdf_thigh + urdf_calf
reach_ik = ik.l2 + ik.l3
mismatch = (abs(urdf_thigh - ik.l2) > 1e-4 or
            abs(urdf_calf - ik.l3) > 1e-4)
report = {
    "status": "FAIL" if mismatch else "PASS",
    "scope": "IK numerical model vs URDF geometry — prerequisite to dynamic gait",
    "urdf_thigh_m": urdf_thigh, "urdf_calf_m": urdf_calf,
    "solver_thigh_m": ik.l2, "solver_calf_m": ik.l3,
    "max_reach_urdf_m": reach_xacro, "max_reach_solver_m": reach_ik,
    "sample_target_xyz_m": list(target),
    "sample_distance_m": math.hypot(target[0], target[2]),
    "sample_solvable_by_urdf_length": math.hypot(target[0], target[2]) <= reach_xacro,
    "sample_clamped_by_solver_length": math.hypot(target[0], target[2]) > reach_ik,
    "sample_ik_angles_rad": [float(x) for x in angles] if angles is not None else None,
    "gait_physics_verdict": "NOT_RUN_UNTIL_GEOMETRY_CONSISTENT",
}
out.write_text(json.dumps(report, indent=2) + "\n")
if mismatch:
    print("CH10_IK_URDF_GEOMETRY_MISMATCH_FOUND " + json.dumps(report), flush=True)
    sys.exit(1)
print("CH10_IK_URDF_LENGTHS_MATCH " + json.dumps(report), flush=True)
