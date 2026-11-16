#!/usr/bin/env python3
"""Issue #181 one-fault DART solver control; no geometry/safety changes.

Original native ECS + static/gravity/pose and contact point geometry confirms
stale contact constraint after 50g dynamic rod separated from real fingers.
Changing collision detector ODE->FCL in CI #43690057020 did NOT fix.
This isolates only the CONTACT CONSTRAINT solver Dantzig(default)->PGS.
"""
import argparse,hashlib,json
from pathlib import Path
import xml.etree.ElementTree as ET
def apply_one_solver_factor(world_path,receipt_path):
    path=Path(world_path)
    original=path.read_bytes()
    tree=ET.ElementTree(ET.fromstring(original))
    world=tree.getroot().find("./world[@name='book_camera']")
    if world is None:raise ValueError("G04B_181_ORIGINAL_WORLD_MISSING")
    physics=world.find("physics")
    if physics is None or world.findtext("gravity","").strip()!="0 0 -9.8":
        raise ValueError("G04B_181_PHYSICS_OR_GRAVITY_NOT_ORIGINAL")
    rod=world.find("./model[@name='g04_grasp_cylinder']")
    if rod is None or rod.findtext("static")!="false" or abs(
        float(rod.findtext("./link[@name='cylinder_link']/inertial/mass","0"))-.05)>1e-9:
        raise ValueError("G04B_181_DYNAMIC_ROD_NOT_ORIGINAL")
    if physics.find("dart") is not None:
        raise ValueError("G04B_181_SOLVER_OR_DETECTOR_ALREADY_OVERRIDDEN")
    snapshot=ET.tostring(tree.getroot())
    dart=ET.SubElement(physics,"dart")
    solver=ET.SubElement(dart,"solver")
    ET.SubElement(solver,"solver_type").text="pgs"
    physics.remove(dart)
    if ET.tostring(tree.getroot())!=snapshot:
        raise ValueError("G04B_181_MULTI_FACTOR_CHANGE")
    physics.append(dart)
    path.write_text(ET.tostring(tree.getroot(),encoding="unicode"))
    report={"hypothesis":"CONTACT_CONSTRAINT_SOLVER_ONLY",
        "before_sha256":hashlib.sha256(original).hexdigest(),
        "changed_only":"world/physics/dart/solver/solver_type",
        "original_solver":"dantzig (DART default)","candidate":"pgs",
        "original_collision_detector":"ode (DART default)",
        "robot_model":"UNCHANGED","rod_mass_kg":.05,
        "world_gravity_z_mps2":-9.8,"original_physics_step":"UNCHANGED",
        "friction_and_contacts":"UNCHANGED","joint_tolerances":"UNCHANGED",
        "forced_attach":False,"teleport":False,
        "G00_G04A":"NOT_RERUN","G04B":"BLOCKED_UNTIL_NATIVE_COMPLETE",
        "G05":"NOT_RUN","Ch10":"HOLD"}
    Path(receipt_path).write_text(json.dumps(report,indent=2)+"\n")
    return report
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--world",required=True);p.add_argument("--receipt",required=True)
    a=p.parse_args();print(json.dumps(apply_one_solver_factor(a.world,a.receipt),sort_keys=True))
