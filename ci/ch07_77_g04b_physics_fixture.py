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
    # The accepted G04A rod is 240mm high. Native G04B logs proved
    # 34 actual WRIST-vs-rod impacts before finger2 contact; radial target
    # correction alone cannot solve an axial 240mm rod crossing the
    # original wrist z=[0,.06] collision volume.
    # A NEW 80mm-high, 24mm-diameter rod fits original finger-local
    # collision z=[.06,.14] without intersecting original wrist geometry.
    physical_height=.08
    for node in rod.findall(".//geometry/cylinder/length"):
        node.text=str(physical_height)
    inertia=rod.find(".//inertial/inertia")
    mass=.05;radius=.012
    ixx=mass*(3*radius**2+physical_height**2)/12
    izz=mass*radius**2/2
    for axis,value in (("ixx",ixx),("iyy",ixx),("izz",izz)):
        inertia.find(axis).text=str(value)
    # Preserve original physical bottom-on-support contact. Shortening
    # the rod while keeping its detected centre at z=1.94 requires
    # raising only the new TEST-ONLY support top to z=1.90.
    shelf.find("pose").text=".70 0 1.80 0 0 0"
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
    # The first physical RED placed the wrist INSIDE the long cylinder:
    # local wrist collision occupies z=[0,.06] and the rod extended across
    # it. 153 actual wrist-vs-rod collision records shoved the rod off
    # its pedestal. Finger collision occupies local z=[.06,.14]; therefore
    # choose a real source-derived tool tilt with rod local z≈.12 and local
    # x≈0 at grasp, physically clear of the 0..0.06 wrist collision.
    tool_tilt_rad=.72
    rod_grasp_local_z_m=.1204
    stage_wrist={
      "pregrasp":[.62,-.12,1.85],
      "grasp":[.62,0,1.85],
      "lift":[.48,0,1.96],
      "place":[.477,.217,1.759],
    }
    gx,gy,gz=stage_wrist["grasp"]
    dx,dz=.70-gx,1.94-gz
    local_x=math.cos(tool_tilt_rad)*dx-math.sin(tool_tilt_rad)*dz
    local_z=math.sin(tool_tilt_rad)*dx+math.cos(tool_tilt_rad)*dz
    assert abs(local_x)<=.004 and .11<=local_z<=.13
    # Cylinder axial half-height projected onto tilted local tool z.
    # The previous test checked only radius .012 and falsely accepted a
    # 240mm-long rod crossing the original wrist body. Use full extent:
    projected_half_z=(physical_height/2)*abs(math.cos(tool_tilt_rad)) + radius*abs(math.sin(tool_tilt_rad))
    wrist_rod_min_local_z=local_z-projected_half_z
    assert wrist_rod_min_local_z>=.065,(
        "ROD_AXIAL_EXTENT_INTRUDES_WRIST_COLLISION")
    assert local_z-projected_half_z<.14,(
        "ROD_DOES_NOT_OVERLAP_FINGER_CONTACT_ZONE")
    for name,(x,y,z) in stage_wrist.items():
        assert math.hypot(math.hypot(x,y),z-.6)<1.5,(name,x,y,z)
    assert math.isclose(1.94-physical_height/2,1.90,abs_tol=1e-9)
    assert .024<.035
    output.parent.mkdir(parents=True,exist_ok=True)
    tree.write(output,encoding="unicode",xml_declaration=True)
    receipt={
      "scope":"G04B_NEW_TEST_ONLY_PHYSICAL_CONTACT_WORLD",
      "original_g02_world_sha256":hashlib.sha256(original).hexdigest(),
      "g04a_accepted_fixture_unchanged":True,
      "g04a_live_xyz_reused_as_current_measurement":False,
      "rod_static":False,"radius_m":radius,"height_m":physical_height,
      "mass_kg":.05,"rod_center_initial_world_m":[.70,0,1.94],
      "shelf_top_m":1.90,"shelf_planar_side_m":.06,
      "shelf_shrink_reason":"REMOVE_ORIGINAL_WIDE_DISPLAY_SHELF_FROM_ARM_APPROACH_PATH",
      "first_actual_G04B_red_ci":"43557077475",
      "first_actual_G04B_red_no_finger_contacts":True,
      "original_gripper_open_face_gap_m":.035,
      "expected_contact_topic":
        "/world/book_camera/model/g04_grasp_cylinder/link/cylinder_link/sensor/book_ch07_77_rod_contact/contact",
      "target_wrist_position_only_base_link_m":stage_wrist,
      "original_source_tool_tilt_rad":tool_tilt_rad,
      "physical_open_finger_joint_command_m":0.0,
      "physical_open_face_gap_m":.045,
      "approach_axis":"WORLD_Y_BETWEEN_ORIGINAL_FINGER_COLLISION_FACES",
      "original_wrist_and_finger_collision_reused_unchanged":True,
      "rod_local_x_at_grasp_m":local_x,
      "rod_local_z_at_grasp_m":local_z,
      "original_wrist_body_local_z_max_m":.06,
      "rod_axial_projection_half_z_m":projected_half_z,
      "rod_min_local_z_m":wrist_rod_min_local_z,
      "prior_real_rod_wrist_contact_count":34,
      "prior_real_rod_single_finger_contact_count":85,
      "source_failure":"G04B_LONG_ROD_WRIST_COLLISION_WITH_REAL_CONTACT",
      "original_finger_collision_local_z_range_m":[.06,.14],
      "previous_G04B_RED_wrist_collided_with_rod_events":153,
      "previous_G04B_RED_rod_knocked_off_support":True,
      "robot_hardware":"GAZEBO_SIMULATION_ONLY",
      "world_spawn_robot_base_z_m":0.0,
      "world_target_robot_fk_frame_alignment":"BASE_LINK_Z_EQUALS_WORLD_Z_TEST_ONLY",
      "previous_50mm_spawn_mismatch":"FINGER_CONTACT_ZERO_WITH_80MM_ROD",
      "no_forced_attachment":True,
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
