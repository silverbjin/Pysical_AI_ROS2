#!/usr/bin/env python3
"""Ch07 #173 G00 strict static composition and optional xacro expansion.

Existing §7.2 camera, §7.6 gripper/GazeboSimSystem are frozen. This new
check only guards the *new combination*, not old accepted functionality.
"""
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ARM = ("joint1", "joint2", "joint3", "joint4", "joint_wrist")
FINGERS = ("joint_finger1", "joint_finger2")


def verify(root, expanded=None):
    pkg=root/"Ch07/ros2_ws/src/vision_basics"
    moveit=root/"Ch07/ros2_ws/src/my_robot_moveit_config"
    wrapper=pkg/"urdf/my_robot.pick_gazebo.urdf.xacro"
    camera=pkg/"urdf/my_robot.ros2_camera_gazebo.xacro"
    ctrl=pkg/"urdf/my_robot.ros2_control.xacro"
    model=pkg/"urdf/my_robot.urdf.xacro"
    yaml=(pkg/"config/ros2_controllers.yaml").read_text()
    moveit_yaml=(moveit/"config/moveit_controllers.yaml").read_text()
    srdf=ET.parse(moveit/"config/my_robot.srdf").getroot()
    root_tag=ET.parse(wrapper).getroot()
    camera_tree=ET.parse(camera).getroot()
    model_tree=ET.parse(model).getroot()
    ctrl_tree=ET.parse(ctrl).getroot()
    includes=[e.attrib["filename"] for e in root_tag if e.tag.endswith("include")]
    assert len(includes)==3, includes
    for expected in ("my_robot.urdf.xacro", "my_robot.ros2_camera_gazebo.xacro",
                     "my_robot.ros2_control.xacro"):
        assert sum(expected in item for item in includes)==1, expected
    plugins=[e for e in root_tag.iter() if e.tag=="plugin"]
    assert len(plugins)==1 and plugins[0].get("filename")=="gz_ros2_control-system"
    assert len([e for e in camera_tree.iter() if e.tag=="sensor" and e.get("type")=="rgbd_camera"])==1
    assert len([e for e in camera_tree.iter() if e.tag=="gz_frame_id" and
                e.text=="camera_optical_frame"])==1
    joints={e.get("name") for e in model_tree.iter() if e.tag=="joint"}
    assert all(n in joints for n in ARM+FINGERS), joints
    controls={e.get("name") for e in ctrl_tree.iter() if e.tag=="joint"}
    assert all(n in controls for n in ARM+FINGERS), controls
    arm_group=next(e for e in srdf if e.tag=="group" and e.get("name")=="arm_group")
    assert any(e.tag=="chain" and e.get("base_link")=="base_link" and
               e.get("tip_link")=="link_wrist" for e in arm_group)
    assert "gripper_group_controller:" in yaml
    assert yaml.count("joint_trajectory_controller/JointTrajectoryController")==2
    assert moveit_yaml.count("type: FollowJointTrajectory")==2
    assert "type: GripperCommand" not in moveit_yaml
    assert "action_ns: follow_joint_trajectory" in moveit_yaml
    assert len([e for e in root_tag.iter() if e.tag=="ros2_control"])==0  # included once
    summary={"status":"STATIC_PASS","scope":"G00_COMPOSITE_XACRO_SOURCE_ONLY",
             "arm_joints":list(ARM),"finger_joints":list(FINGERS),
             "rgbd_includes":1,"controller_plugin_includes":1,
             "original_camera_and_gripper_source_modified":False,
             "physical_runtime":"NOT_RUN","ch10":"HOLD"}
    if expanded:
        urdf=ET.parse(expanded).getroot()
        assert sum(e.tag=="sensor" and e.get("type")=="rgbd_camera" for e in urdf.iter())==1
        assert sum(e.tag=="plugin" and e.get("filename")=="gz_ros2_control-system"
                   for e in urdf.iter())==1
        assert sum(e.tag=="ros2_control" for e in urdf.iter())==1
        actual={e.get("name") for e in urdf.iter() if e.tag=="joint"}
        assert all(n in actual for n in ARM+FINGERS)
        summary["expanded_urdf"]="PASS"
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--expanded",type=Path)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    try:
        result=verify(args.root,args.expanded)
        if args.out:
            args.out.parent.mkdir(parents=True,exist_ok=True)
            args.out.write_text(json.dumps(result,indent=2)+"\n")
        print("CH07_77_G00_COMPOSITION_STATIC_PASS "+json.dumps(result))
    except Exception as exc:
        print("CH07_77_G00_FAIL "+repr(exc),file=sys.stderr)
        raise
