#!/usr/bin/env python3
"""G04A test-only dynamic object geometry from already accepted G02 world.

Original Gazebo/world fixture is read-only; this adjustment is a NEW
physical graspability boundary, not a re-run of the accepted big cylinder.
No robot command/teleport/physical attach is used here.
"""
import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def build(src,dst,receipt):
    root=ET.parse(src)
    world=root.find(".//world[@name='book_camera']")
    assert world is not None
    sensors=world.findall("./plugin[@name='gz::sim::systems::Sensors']")
    assert len(sensors)==1 and sensors[0].findtext("render_engine")=="ogre2"
    target=world.find("./model[@name='g02_red_cylinder']")
    shelf=world.find("./model[@name='g02_test_shelf']")
    assert target is not None and shelf is not None
    assert target.findtext("static")=="false"
    target.attrib["name"]="g04_grasp_cylinder"
    target.find("pose").text="0.80 0 1.94 0 0 0"
    for p in target.findall(".//geometry/cylinder/radius"):
        p.text="0.012"
    for p in target.findall(".//geometry/cylinder/length"):
        p.text="0.24"
    target.find(".//inertial/mass").text="0.05"
    # Exact solid-cylinder inertia for m=.05kg, r=.012m, h=.24m.
    inertia=target.find(".//inertial/inertia")
    mass,radius,height=.05,.012,.24
    ixx=mass*(3*radius**2+height**2)/12
    izz=mass*radius**2/2
    for name,value in (("ixx",ixx),("iyy",ixx),("izz",izz)):
        inertia.find(name).text=str(value)
    shelf.attrib["name"]="g04_support"
    shelf.find("pose").text="0.80 0 1.72 0 0 0"
    # Shelf upper surface is z=1.82; cylinder bottom is also z=1.82.
    target_center=1.94
    assert math.isclose(target_center-height/2,1.82,abs_tol=1e-10)
    # Destination shelf for subsequent G04B, not a simulated grasp.
    bin_model=ET.SubElement(world,"model",{"name":"g04_bin_support"})
    ET.SubElement(bin_model,"static").text="true"
    ET.SubElement(bin_model,"pose").text="0.55 0.25 1.63 0 0 0"
    link=ET.SubElement(bin_model,"link",{"name":"bin_support"})
    for typ in ("collision","visual"):
        e=ET.SubElement(link,typ,{"name":"bin_"+typ})
        geom=ET.SubElement(e,"geometry")
        ET.SubElement(ET.SubElement(geom,"box"),"size").text="0.30 0.30 0.20"
    # Grasp centre + cylinder geometry is physically reachable by a
    # 0.5+1.0 m 2R wrist model; no IK/collision/physical result asserted.
    grip_wrist=[.8,0,1.84]
    reach=math.hypot(.8,grip_wrist[2]-.6)
    clearance_between_open_finger_collision_faces_m=.06-2*.005-.015
    assert reach<1.5 and .024<clearance_between_open_finger_collision_faces_m
    record={"scope":"G04A_TEST_ONLY_GRASPABLE_OBJECT_GEOMETRY",
            "original_g02_sdf_unchanged":True,
            "sensors_plugin_count":1,"static":False,
            "dynamic_model":"g04_grasp_cylinder",
            "center_world_m":[.8,0,1.94],
            "radius_m":radius,"diameter_m":2*radius,
            "height_m":height,"mass_kg":mass,
            "support_top_z_m":1.82,
            "gripper_collision_face_gap_at_open_m":clearance_between_open_finger_collision_faces_m,
            "proposed_wrist_xyz_m":grip_wrist,
            "proposed_wrist_distance_from_shoulder_m":reach,
            "geometric_diameter_clearance":"PASS",
            "geometric_2R_wrist_reach":"PASS",
            "IK_collision":"NOT_RUN","MoveIt":"NOT_RUN",
            "physical_contact":"NOT_RUN","lift":"NOT_RUN","place":"NOT_RUN","Ch10":"HOLD"}
    dst.parent.mkdir(parents=True,exist_ok=True)
    root.write(dst,encoding="unicode",xml_declaration=True)
    receipt.write_text(json.dumps(record,indent=2)+"\n")
    print("CH07_77_G04A_GRASPABLE_DYNAMIC_CYLINDER_SDF_STATIC_PASS")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--receipt",type=Path,required=True)
    a=p.parse_args()
    build(a.source,a.output,a.receipt)
