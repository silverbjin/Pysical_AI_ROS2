#!/usr/bin/env python3
"""Read-only prerequisite audit. Detected blocks are not successes."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
out=root/"ci-results/extended/prerequisites"
out.mkdir(parents=True,exist_ok=True)
moveit=root/"Ch06/ros2_ws/src/my_robot_moveit_config"
moveit_source=root/"Ch06/ros2_ws/src/my_robot_control/my_robot_control/hello_moveit.py"
missing_urdf=not (moveit/"urdf/my_robot.urdf").is_file()
requires_path='file_path="urdf/my_robot.urdf"' in moveit_source.read_text()
camera=root/"Ch07/ros2_ws/src/vision_basics"
base_text=(camera/"urdf/my_robot.urdf.xacro").read_text()
camera_default=("<sensor" in base_text and "camera" in base_text)
setup=(camera/"setup.py").read_text()
subscriber_registered="simple_image_subscriber =" in setup
camera_variants=sorted(x.name for x in (camera/"urdf").glob("*camera*xacro"))
results={
 "Ch06_6_4":{"status":"BLOCKED" if missing_urdf and requires_path else "RECHECK_REQUIRED",
             "source_references_urdf":requires_path,"referenced_urdf_exists":not missing_urdf,
             "dynamic_moveit_planning":"NOT_RUN"},
 "Ch07_7_2":{"status":"BLOCKED" if not camera_default and not subscriber_registered else "RECHECK_REQUIRED",
             "default_urdf_has_camera":camera_default,
             "image_subscriber_installed":subscriber_registered,
             "camera_variant_candidates":camera_variants,
             "dynamic_gazebo_camera":"NOT_RUN"}}
(out/"results.json").write_text(json.dumps(results,indent=2,ensure_ascii=False)+"\n")
for name,value in results.items():print(name,value["status"],json.dumps(value,ensure_ascii=False),flush=True)
assert missing_urdf and requires_path,"Ch06 known blocker changed; manual re-evaluation required"
assert not camera_default and not subscriber_registered,"Ch07 known blocker changed; manual re-evaluation required"
print("READ_ONLY_PREREQUISITE_AUDIT_DONE_UNRESOLVED_ARE_NOT_PASS",flush=True)
