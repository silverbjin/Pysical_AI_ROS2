#!/usr/bin/env python3
"""Issue #181, DART 6.13.2 bounded *test-fixture-only* lower-limit margin.

Upstream Gazebo Sim #1684 / DART #2086/#2421 documented servo joints locked
at the exact position limit. Move only SDF *physics lower limits* outwards by
1mm for original finger1/2. No URDF, command limits, collision, joint axes,
gains, object attachments or physical PASS tolerances may change.
"""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

LOWER_MARGIN_M=.001
ORIGINAL_LOWER_M=0.
ORIGINAL_UPPER_M=.025
FINGERS={"joint_finger1":"1 0 0","joint_finger2":"-1 0 0"}
ANCHOR_NAME="g04b_test_only_world_to_base_fixed"

def apply_test_only_dart_margin(source):
    root=ET.fromstring(source)
    if root.tag!="sdf":raise ValueError("G04B_DART_SDF_REQUIRED")
    model=root.find("./model[@name='my_robot']")
    if model is None or len(root.findall('./model'))!=1:
        raise ValueError("G04B_DART_ORIGINAL_MODEL_REQUIRED")
    if model.findtext("static",default="false").strip().lower()!="false":
        raise ValueError("G04B_DART_REAL_DYNAMIC_ROBOT_REQUIRED")
    joints=model.findall("joint")
    if len(joints)!=8 or {j.get("name") for j in joints}!={*FINGERS,ANCHOR_NAME,
         "joint1","joint2","joint3","joint4","joint_wrist"}:
        raise ValueError("G04B_DART_ORIGINAL_7_JOINTS_PLUS_ANCHOR_REQUIRED")
    if model.findtext("./joint[@name='"+ANCHOR_NAME+"']/parent")!="world":
        raise ValueError("G04B_DART_ONLY_EXISTING_WORLD_FIXED_FIXTURE_ALLOWED")
    before=ET.tostring(root)
    for name,axis in FINGERS.items():
        j=model.find("./joint[@name='"+name+"']")
        if j is None or j.get("type")!="prismatic" or j.findtext("parent")!="link_wrist":
            raise ValueError("G04B_DART_ORIGINAL_FINGER_JOINT_REQUIRED_"+name)
        xyz=" ".join(j.findtext("axis/xyz",default="").split())
        if xyz!=axis:raise ValueError("G04B_DART_ORIGINAL_JOINT_AXIS_CHANGED_"+name)
        lo=j.find("axis/limit/lower")
        hi=j.find("axis/limit/upper")
        if lo is None or hi is None or abs(float(lo.text)-ORIGINAL_LOWER_M)>1e-9 or abs(float(hi.text)-ORIGINAL_UPPER_M)>1e-9:
            raise ValueError("G04B_DART_ORIGINAL_JOINT_LIMITS_NOT_FOUND_"+name)
        lo.text="-0.001"
    result=ET.tostring(root,encoding="unicode")
    checker=deepcopy(root)
    for name in FINGERS:
        checker.find("./model/joint[@name='"+name+"']/axis/limit/lower").text="0"
    # Compare normalized XML value semantics: the source lower string '0'
    # in gz sdf conversion is exactly '0'. All other attrs/components equal.
    if ET.tostring(checker)!=before:
        raise ValueError("G04B_DART_MULTI_FACTOR_OR_GEOMETRY_CHANGE")
    return result,{
      "scope":"ONE_TEST_ONLY_DART_LOWER_LIMIT_MARGIN",
      "upstream_references":["gazebosim/gz-sim#1684",
         "dartsim/dart#2086","dartsim/dart#2421","dartsim/dart#2424"],
      "source_sdf_sha256":hashlib.sha256(source.encode()).hexdigest(),
      "result_sdf_sha256":hashlib.sha256(result.encode()).hexdigest(),
      "changed_joint_fields":["joint_finger1/axis/limit/lower",
                              "joint_finger2/axis/limit/lower"],
      "sdf_physical_lower_m":-LOWER_MARGIN_M,
      "original_urdf_and_controller_command_lower_m":ORIGINAL_LOWER_M,
      "original_upper_m":ORIGINAL_UPPER_M,
      "robot_7_original_joint_axes_and_links_unchanged":True,
      "joint_position_cmd_and_tolerance_unchanged":True,
      "contact_rod_gravity_friction_or_pose_unchanged":True,
      "real_rod_attach_or_teleport":False,
      "G00_G04A":"NOT_RERUN",
      "G04B":"BLOCKED_PENDING_NATIVE_REAL_GAZEBO",
      "G05":"NOT_RUN","Ch10":"HOLD"}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--receipt",required=True)
    a=ap.parse_args()
    src=Path(a.input).read_text()
    output,receipt=apply_test_only_dart_margin(src)
    Path(a.output).write_text(output)
    Path(a.receipt).write_text(json.dumps(receipt,indent=2)+"\n")
    print("G04B_181_ONE_DART_6_13_LOWER_MARGIN_CANDIDATE_NOT_PHYSICAL_PASS")
if __name__=="__main__":main()
