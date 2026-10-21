"""Offline Ch06 KDL configuration and SRDF group contract check (stdlib only)."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


def validate(kinematics_text, srdf_text):
    errors = []
    import re
    def get(key):
        match = re.search(r"^  " + re.escape(key) + r":\s*([^#\n]+)", kinematics_text, re.M)
        return match.group(1).strip() if match else None

    if not re.search(r"^arm_group:\s*$", kinematics_text, re.M):
        errors.append("missing arm_group")
    if get("kinematics_solver") != "kdl_kinematics_plugin/KDLKinematicsPlugin":
        errors.append("KDL solver id mismatch")
    try:
        timeout = float(get("kinematics_solver_timeout") or "nan")
        if not 0.005 <= timeout <= 1.0:
            errors.append("timeout outside teaching range")
    except ValueError:
        errors.append("invalid timeout")
    if get("position_only_ik") not in ("true", "True"):
        errors.append("5-DOF demo must explicitly mark position_only_ik")

    try:
        root = ET.fromstring(srdf_text)
        arm = root.find("./group[@name='arm_group']")
        if arm is None or arm.find("chain") is None:
            errors.append("arm_group chain missing in SRDF")
        else:
            chain = arm.find("chain")
            if chain.get("base_link") != "base_link" or chain.get("tip_link") != "link_wrist":
                errors.append("SRDF chain endpoints mismatch")
            names = [j.get("name") for j in arm.findall("joint")]
            active = [n for n in names if n != "virtual_joint"]
            if active != ["joint1", "joint2", "joint3", "joint4", "joint_wrist"]:
                errors.append("joint mapping differs from Ch06 five-axis contract")
    except ET.ParseError as exc:
        errors.append(f"invalid SRDF: {exc}")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    cfg = args.root / "ros2_ws/src/my_robot_moveit_config/config"
    errors = validate((cfg / "kinematics.yaml").read_text(encoding="utf-8"),
                      (cfg / "my_robot.srdf").read_text(encoding="utf-8"))
    for item in errors:
        print("FAIL:", item)
    if not errors:
        print("PASS: static 5-DOF KDL XYZ / SRDF contract")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
