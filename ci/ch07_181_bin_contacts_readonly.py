#!/usr/bin/env python3
"""Cycle07: add READ-ONLY contact SENSOR to existing bin support collision.

The entire test world physics, robot, rod, bin geometry, gravity and
friction must remain identical. Contact sensor observes native bin pairs,
not a fictitious collision, and cannot assert G04B success.
"""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
SENSOR_NAME="g04b_cycle07_bin_contacts"
BIN_TOPIC="/world/book_camera/model/g04_bin_support/link/bin_support/sensor/"+SENSOR_NAME+"/contact"

def add_bin_contact_sensor(world_path,receipt_path):
    p=Path(world_path)
    original=p.read_bytes()
    root=ET.fromstring(original)
    world=root.find("./world[@name='book_camera']")
    if world is None:raise ValueError("CYCLE07_WORLD_MISSING")
    binmodel=world.find("./model[@name='g04_bin_support']")
    if binmodel is None or binmodel.findtext("static")!="true":
        raise ValueError("CYCLE07_STATIC_BIN_MISSING")
    link=binmodel.find("./link[@name='bin_support']")
    col=link.find("./collision[@name='bin_collision']") if link is not None else None
    if col is None or col.findtext("./geometry/box/size","").strip()!="0.30 0.30 0.20":
        raise ValueError("CYCLE07_BIN_COLLISION_CHANGED")
    if link.find("./sensor[@name='"+SENSOR_NAME+"']") is not None:
        raise ValueError("CYCLE07_DUPLICATE_SENSOR")
    contact_plugin=[x for x in world.findall("plugin")
        if x.get("filename")=="gz-sim-contact-system"]
    if len(contact_plugin)!=1:
        raise ValueError("CYCLE07_CONTACT_SYSTEM_MISSING")
    snapshot=ET.tostring(root)
    sensor=ET.SubElement(link,"sensor",{"name":SENSOR_NAME,"type":"contact"})
    ET.SubElement(sensor,"always_on").text="true"
    ET.SubElement(sensor,"update_rate").text="100"
    ET.SubElement(ET.SubElement(sensor,"contact"),"collision").text="bin_collision"
    link.remove(sensor)
    if ET.tostring(root)!=snapshot:
        raise ValueError("CYCLE07_WORLD_MUTATION_OTHER_THAN_SENSOR")
    link.append(sensor)
    p.write_text(ET.tostring(root,encoding="unicode"))
    report={"kind":"READ_ONLY_NATIVE_BIN_CONTACT",
      "original_world_sha256":hashlib.sha256(original).hexdigest(),
      "changed_only":"g04_bin_support/bin_support/sensor",
      "native_topic":BIN_TOPIC,
      "bin_shape_m":[.30,.30,.20],"bin_collision":"UNCHANGED",
      "robot_joints":"UNCHANGED","physics_solver":"UNCHANGED",
      "friction_mass_gravity":"UNCHANGED","commands_goals":"UNCHANGED",
      "G04B":"BLOCKED_UNTIL_REAL_PHYSICAL_ACCEPTANCE"}
    Path(receipt_path).write_text(json.dumps(report,indent=2)+"\n")
    return report
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--world",required=True)
    a.add_argument("--receipt",required=True)
    x=a.parse_args()
    print(json.dumps(add_bin_contact_sensor(x.world,x.receipt),sort_keys=True))
