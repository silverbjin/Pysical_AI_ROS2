"""Check whether Ch06's virtual joint and robot root are defined exactly once."""
from pathlib import Path
import xml.etree.ElementTree as ET


def check(urdf_text, srdf_text):
    errors = []
    try:
        urdf = ET.fromstring(urdf_text)
        srdf = ET.fromstring(srdf_text)
    except ET.ParseError as error:
        return [f"XML parse error: {error}"]
    if urdf.tag != "robot" or srdf.tag != "robot":
        errors.append("robot root element missing")
    if urdf.find("./link[@name='world']") is not None:
        errors.append("world link inside URDF duplicates SRDF virtual root")
    if urdf.find("./joint[@name='world_to_base_joint']") is not None:
        errors.append("world fixed joint duplicates SRDF virtual root")
    joints = srdf.findall("./virtual_joint")
    if len(joints) != 1 or joints[0].get("child_link") != "base_link":
        errors.append("expected one SRDF virtual world->base_link joint")
    arm = srdf.find("./group[@name='arm_group']")
    if arm is None:
        errors.append("missing arm_group")
    else:
        if any(j.get("name") == "virtual_joint" for j in arm.findall("joint")):
            errors.append("virtual joint must not be listed as arm's actuated joint")
        chain = arm.find("chain")
        if chain is None or chain.get("tip_link") != "link_wrist":
            errors.append("arm chain must terminate at link_wrist")
    return errors


if __name__ == "__main__":
    cfg = Path(__file__).resolve().parents[1] / "ros2_ws/src/my_robot_moveit_config/config"
    issues = check((cfg / "my_robot.urdf.xacro").read_text(encoding="utf-8"),
                   (cfg / "my_robot.srdf").read_text(encoding="utf-8"))
    for issue in issues:
        print("FAIL:", issue)
    if not issues:
        print("PASS: URDF/SRDF root and arm group contract")
    raise SystemExit(bool(issues))
