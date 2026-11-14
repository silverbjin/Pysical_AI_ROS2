#!/usr/bin/env python3
"""G04B test-only dynamic physical grasp world with native Contact sensor.

G04A vision fixture remains immutable; this NEW physical trial moves the
same grippable 24mm rod/shelf 0.10m inward to clear arm-link/shelf geometry.
Thus do not claim G04A's measured xyz as live data in this shifted world.
"""
import argparse,hashlib,json,math
from pathlib import Path
import xml.etree.ElementTree as ET
from ch07_77_g04a_graspable_fixture import build as g04a_build

def build(source, output, audit):
    original=source.read_bytes()
    intermediate=output.with_suffix(".intermediate.sdf")
    inter_receipt=output.with_suffix(".intermediate.json")
    g04a_build(source,intermediate,inter_receipt)
    tree=ET.parse(intermediate)
    world=tree.getroot().find("./world[@name='book_camera']")
    assert world is not None
    rod=world.find("./model[@name='g04_grasp_cylinder']")
    shelf=world.find("./model[@name='g04_support']")
    assert rod is not None and shelf is not None
    # Shift with an explicit derivative fixture, avoiding accepted G04A edits.
    rod.find("pose").text=".70 0 1.94 0 0 0"
    shelf.find("pose").text=".70 0 1.72 0 0 0"
    # The G04A 0.50m-wide optical display shelf occupies the approaching
    # arm link4 swept volume. In the first real physics RED (CI #43557077475)
    # the arm succeeded within loose joint goal tolerances but its actual
    # fingertip centre missed the rod by 4cm; no finger contact events
    # occurred. Reduce ONLY this new test-only support to a 0.06m pedestal.
    # Its upper surface stays z=1.82m and supports the full 0.024m rod.
    for shape in ("collision","visual"):
        node=shelf.find("./link/"+shape+"/geometry/box/size")
        assert node is not None and node.text.strip()=="0.50 0.50 0.20"
        node.text="0.06 0.06 0.20"
    assert rod.findtext("static")=="false"
    ET.SubElement(world,"plugin",{"filename":"gz-sim-contact-system",
        "name":"gz::sim::systems::Contact"})
    link=rod.find("./link[@name='cylinder_link']")
    assert link is not None
    sensor=ET.SubElement(link,"sensor",{"name":"book_ch07_77_rod_contact",
                                        "type":"contact"})
    ET.SubElement(sensor,"always_on").text="true"
    ET.SubElement(sensor,"update_rate").text="100"
    ET.SubElement(ET.SubElement(sensor,"contact"),"collision").text="cylinder_collision"
    # Explicit nominal wrist solutions are checked in full G04B MoveGroup,
    # not presumed safe by this geometry-only contract.
    stage_wrist={
      "pregrasp":[.57,0,1.90],
      "grasp":[.70,0,1.90],
      "lift":[.54,0,1.965],
      "place":[.55,.25,1.75],
    }
    for name,(x,y,z) in stage_wrist.items():
        assert math.hypot(math.hypot(x,y),z-.6)<1.5,(name,x,y,z)
    assert math.isclose(1.94-.24/2,1.82,abs_tol=1e-9)
    assert .024<.035
    output.parent.mkdir(parents=True,exist_ok=True)
    tree.write(output,encoding="unicode",xml_declaration=True)
    receipt={
      "scope":"G04B_NEW_TEST_ONLY_PHYSICAL_CONTACT_WORLD",
      "original_g02_world_sha256":hashlib.sha256(original).hexdigest(),
      "g04a_accepted_fixture_unchanged":True,
      "g04a_live_xyz_reused_as_current_measurement":False,
      "rod_static":False,"radius_m":.012,"height_m":.24,
      "mass_kg":.05,"rod_center_initial_world_m":[.70,0,1.94],
      "shelf_top_m":1.82,"shelf_planar_side_m":.06,
      "shelf_shrink_reason":"REMOVE_ORIGINAL_WIDE_DISPLAY_SHELF_FROM_ARM_APPROACH_PATH",
      "first_actual_G04B_red_ci":"43557077475",
      "first_actual_G04B_red_no_finger_contacts":True,
      "original_gripper_open_face_gap_m":.035,
      "expected_contact_topic":
        "/world/book_camera/model/g04_grasp_cylinder/link/cylinder_link/sensor/book_ch07_77_rod_contact/contact",
      "target_wrist_position_only_base_link_m":stage_wrist,
      "robot_hardware":"GAZEBO_SIMULATION_ONLY","no_forced_attachment":True,
      "no_set_pose_or_teleport":True,
      "real_contact":"NOT_RUN","lift":"NOT_RUN","place":"NOT_RUN","Ch10":"HOLD"
    }
    audit.write_text(json.dumps(receipt,indent=2)+"\n")
    intermediate.unlink(missing_ok=True)
    inter_receipt.unlink(missing_ok=True)
    print("CH07_77_G04B_PHYSICS_FIXTURE_STATIC_PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--receipt",type=Path,required=True)
    a=p.parse_args()
    build(a.source,a.output,a.receipt)
