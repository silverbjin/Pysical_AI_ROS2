#!/usr/bin/env python3
"""Issue #181: ONE controlled TEST-ONLY DART collision detector comparison.

Original pinned Gazebo Sim8 defaults DART collision detector to "ode".
Immutable raw CI #43689418982:
  Static=false; World Gravity z=-9.8; rod stops at z~2.0757;
  native sensor contact points are >8cm from the real finger link,
  although original finger collision enclosing radius is ~4.3cm.
This warrants ONE detector-only collision-manifold hypothesis (fcl).
The robot, friction, contact sensors, damping, DART solver, controller,
Goal tolerance, original source world and published accepted tests remain
unchanged. A physical test must still fail closed on any G04B rejection.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ORIGINAL_DEFAULT_DETECTOR="ode"
CANDIDATE_DETECTOR="fcl"

def isolate_one_detector_factor(world_sdf,receipt_json):
    path=Path(world_sdf)
    receipt=Path(receipt_json)
    original=path.read_bytes()
    root=ET.fromstring(original)
    world=root.find("./world[@name='book_camera']")
    if world is None:raise ValueError("G04B_181_DART_WORLD_INVALID")
    physics=world.find("./physics")
    if physics is None:raise ValueError("G04B_181_ORIGINAL_PHYSICS_MISSING")
    if world.findtext("gravity","").strip()!="0 0 -9.8":
        raise ValueError("G04B_181_WORLD_GRAVITY_MISMATCH")
    original_rod=world.find("./model[@name='g04_grasp_cylinder']")
    if original_rod is None or original_rod.findtext("static")!="false":
        raise ValueError("G04B_181_ORIGINAL_DYNAMIC_ROD_MISSING")
    mass=original_rod.findtext("./link[@name='cylinder_link']/inertial/mass")
    if mass is None or abs(float(mass)-.05)>1e-9:
        raise ValueError("G04B_181_ORIGINAL_ROD_MASS_MISMATCH")
    if physics.find("./dart") is not None:
        raise ValueError("G04B_181_DART_NONDEFAULT_CONFIG_REQUIRES_AUDIT")
    snapshot=ET.tostring(root)
    dart=ET.SubElement(physics,"dart")
    child=ET.SubElement(dart,"collision_detector")
    child.text=CANDIDATE_DETECTOR
    # Mutation contract: stripping the one new subtree yields byte-identical
    # XML element serialization to before (no changes to models, contacts,
    # mass, physics timestep or integration solver).
    physics.remove(dart)
    assert ET.tostring(root)==snapshot,"G04B_181_MORE_THAN_ONE_CHANGE"
    physics.append(dart)
    path.write_text(ET.tostring(root,encoding="unicode"))
    out={"scope":"G04B_181_ONE_DART_CONTACT_MANIFOLD_HYPOTHESIS",
         "source_world_before_sha256":hashlib.sha256(original).hexdigest(),
         "only_changed_sdf_element":"world/physics/dart/collision_detector",
         "original_default_detector":ORIGINAL_DEFAULT_DETECTOR,
         "candidate_detector":CANDIDATE_DETECTOR,
         "same_dart_solver":True,"same_world_gravity":True,
         "same_physics_step":True,"same_robot":True,
         "same_gripper_goal_tolerance":True,
         "same_rod_mass":True,"same_rod_geometry":True,
         "same_friction_and_materials":True,
         "force_attach_or_teleport":False,
         "G00_G04A":"NOT_RERUN",
         "G04B":"BLOCKED_PENDING_REAL_NATIVE_EVIDENCE",
         "G05":"NOT_RUN","Ch10":"HOLD"}
    receipt.write_text(json.dumps(out,indent=2)+"\n")
    return out

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--world",required=True)
    parser.add_argument("--receipt",required=True)
    args=parser.parse_args()
    print(json.dumps(isolate_one_detector_factor(args.world,args.receipt),
                     sort_keys=True))
