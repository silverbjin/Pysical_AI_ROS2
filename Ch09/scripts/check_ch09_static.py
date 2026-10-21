#!/usr/bin/env python3
"""Chapter 09 dependency-free, source-only validation (no ROS/Gazebo imports).

Usage: python3 Ch09/scripts/check_ch09_static.py [--strict] [--root PATH]
Strict checks require the 9.1--9.7 fixes to be merged into the target checkout.
"""
import argparse
import ast
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def inspect_tree(package: Path, strict: bool = False) -> dict:
    results = []

    def test(name: str, condition: bool, details: str = "") -> None:
        results.append({"name": name, "status": "PASS" if condition else "FAIL", "details": details})

    for path in sorted(package.rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            test(f"python_ast:{path.relative_to(package)}", True)
        except (SyntaxError, UnicodeError) as exc:
            test(f"python_ast:{path.relative_to(package)}", False, str(exc))

    for path in sorted(package.rglob("*.xacro")) + sorted(package.rglob("*.xml")) + sorted(package.rglob("*.sdf")):
        try:
            ET.parse(path)
            test(f"xml:{path.relative_to(package)}", True)
        except ET.ParseError as exc:
            test(f"xml:{path.relative_to(package)}", False, str(exc))

    robot = package / "urdf" / "robot.urdf.xacro"
    leg = package / "urdf" / "parts" / "leg.xacro"
    props = package / "urdf" / "common" / "robot_properties.xacro"
    bridge = package / "config" / "ros_gz_bridge.yaml"
    setup = package / "setup.py"
    display = package / "launch" / "display.launch.py"
    simulation = package / "launch" / "simulation.launch.py"
    stand_up = package / "my_quadruped_bot" / "stand_up.py"
    single = package / "my_quadruped_bot" / "single_leg_mover.py"
    required = [robot, leg, props, bridge, setup, display, simulation, stand_up, single]
    for path in required:
        test(f"required:{path.relative_to(package)}", path.is_file())

    if all(path.is_file() for path in required):
        robot_text = robot.read_text(encoding="utf-8")
        bridge_text = bridge.read_text(encoding="utf-8")
        properties = ET.parse(props).getroot()
        xns = "{http://www.ros.org/wiki/xacro}property"
        vals = {}
        for element in properties.findall(xns):
            try:
                vals[element.get("name")] = float(element.get("value"))
            except (TypeError, ValueError):
                pass
        keys = ("base_mass", "hip_mass", "thigh_mass", "calf_mass")
        test("mass_properties_exist", all(k in vals for k in keys))
        if all(k in vals for k in keys):
            # The foot sphere has a fixed 0.10 kg mass in the current leg macro.
            mass = vals["base_mass"] + 4.0 * (
                vals["hip_mass"] + vals["thigh_mass"] + vals["calf_mass"] + 0.10
            )
            test("nominal_total_mass_12kg", abs(mass - 12.0) < 1e-9, f"mass={mass}")
        test("four_leg_macro_calls", len(re.findall(r"<xacro:leg\s+prefix=", robot_text)) == 4)
        test("twelve_bridge_commands", len(re.findall(r"^\s*direction:\s*ROS_TO_GZ\s*$", bridge_text, re.M)) == 12)
        for kind in ("hip", "thigh", "calf"):
            test(f"leg_joint:{kind}", f'name="${{prefix}}_{kind}_joint"' in leg.read_text(encoding="utf-8"))

        if strict:
            leg_text = leg.read_text(encoding="utf-8")
            test("strict_rviz_package", "my_robot_description" not in display.read_text(encoding="utf-8"))
            test("strict_sim_time", "use_sim_time" in simulation.read_text(encoding="utf-8"))
            test("strict_friction", "<mu1>" in leg_text and "<mu2>" in leg_text)
            test("strict_thigh_inertia", 'xyz="0 0 ${-thigh_length/2.0}"' in leg_text)
            test("strict_calf_inertia", 'xyz="0 0 ${-calf_length/2.0}"' in leg_text)
            test("strict_hip_lateral", 'box size="0.04 ${hip_length} 0.04"' in leg_text)
            test("strict_stand_ramp", "ramp_seconds" in stand_up.read_text(encoding="utf-8"))
            test("strict_single_leg_owner", "JOINT_TYPES" in single.read_text(encoding="utf-8"))

    failed = [item for item in results if item["status"] == "FAIL"]
    return {"pass": not failed, "checks": len(results), "passed": len(results) - len(failed), "failed": len(failed), "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / "ros2_ws" / "src" / "my_quadruped_bot", help="Path to Ch09 ROS 2 package")
    parser.add_argument("--strict", action="store_true", help="Require fixes in 9.1--9.7 branches to be merged")
    parser.add_argument("--output", type=Path, help="Write JSON evidence to this file")
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error(f"Package directory does not exist: {args.root}")
    result = inspect_tree(args.root, strict=args.strict)
    result["root"] = str(args.root.resolve())
    result["strict"] = args.strict
    data = json.dumps(result, ensure_ascii=False, indent=2)
    print(data)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data + "\n", encoding="utf-8")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
