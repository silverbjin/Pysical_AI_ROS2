#!/usr/bin/env python3
"""Read-only preserved evidence audit: never labels blocked or archived work PASS."""
from pathlib import Path
import json
import re

root=Path(__file__).resolve().parents[1]
out=root/"ci-results/vision/audit"
out.mkdir(parents=True,exist_ok=True)

moveit=root/"Ch06/ros2_ws/src/my_robot_moveit_config"
client=root/"Ch06/ros2_ws/src/my_robot_control/my_robot_control/hello_moveit.py"
camera=root/"Ch07/ros2_ws/src/vision_basics"
ch13=root/"Ch13/evidence/section_13_8_policy/book_closeout_v53_20261112.json"
client_code=client.read_text()
missing_moveit=(not (moveit/"urdf/my_robot.urdf").exists() and
                'file_path="urdf/my_robot.urdf"' in client_code)
camera_variant=(camera/"urdf/my_robot.ros2_camera_gazebo.urdf.xacro").exists()
camera_sensor=(camera/"urdf/my_robot.ros2_camera_gazebo.xacro").read_text()
archived=json.loads(ch13.read_text())
cases=archived.get("selected_actual_cases",[])
assert len(cases)==2,"Historic evidence no longer has two basic cases"
assert archived.get("owner_acceptance")=="pending_user_review"
for c in cases:
    assert c["basic_result"]=="PASS" and c["full_mission_success"] is False
    assert all(c["checks"].values())
    assert re.fullmatch("[a-f0-9]{64}",c["source_manifest_sha256"])

result={
 "Ch06":{"status":"BLOCKED" if missing_moveit else "RECHECK_REQUIRED",
         "missing_source_URDF":missing_moveit,"moveit_execution":"NOT_RUN"},
 "Ch07":{"camera_variant_available":camera_variant,
         "variant_has_actual_rgbd_sensor":'type="rgbd_camera"' in camera_sensor,
         "camera_ros_runtime":"SEPARATE_LIVE_CI"},
 "Ch09":{"status":"PREVIOUS_COMMAND_AND_STATE_PASS",
         "body_stability":"NOT_RUN","fall_or_ground_contact":"NOT_RUN"},
 "Ch10":{"status":"HOLD_DO_NOT_RUN","issue":123},
 "Ch13":{"status":"PRESERVED_HISTORICAL_BASIC_EVIDENCE",
         "cases":[{"scenario":x["scenario"],"basic_result":x["basic_result"]} for x in cases],
         "owner_acceptance":archived["owner_acceptance"],
         "full_mission_accepted":False,
         "new_live_engine_run":"NOT_RUN"},
}
(out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
assert missing_moveit and camera_variant
print("PRESERVED_BOUNDARY_AUDIT_PASS_NOT_FULL_CHAPTER_ACCEPTANCE",flush=True)
