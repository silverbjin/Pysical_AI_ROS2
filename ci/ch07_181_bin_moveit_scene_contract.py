"""Cycle08: map unchanged Gazebo bin collision into MoveIt planning scene.

The G04B test robot base_link is world-fixed at origin. Reject any geometry
deviation or unaccounted collision/link transform. No ROS/Gazebo imports.
"""
import math
import xml.etree.ElementTree as ET
from pathlib import Path

def exact_bin_collision_from_world(path):
    root=ET.parse(Path(path)).getroot()
    world=root.find("./world[@name='book_camera']")
    if world is None:raise ValueError("C08_WORLD_MISSING")
    model=world.find("./model[@name='g04_bin_support']")
    if model is None or model.findtext("static")!="true":
        raise ValueError("C08_STATIC_BIN_MISSING")
    link=model.find("./link[@name='bin_support']")
    box=(link.find("./collision[@name='bin_collision']")
         if link is not None else None)
    if box is None:raise ValueError("C08_BIN_COLLISION_MISSING")
    if link.find("pose") is not None or box.find("pose") is not None:
        raise ValueError("C08_LOCAL_COLLISION_TRANSFORM_UNACCOUNTED")
    xyzrpy=model.findtext("pose","").split()
    size=box.findtext("./geometry/box/size","").split()
    if len(xyzrpy)!=6 or len(size)!=3:
        raise ValueError("C08_INVALID_BIN_DIMENSIONS")
    values=[float(x) for x in xyzrpy+size]
    if not all(math.isfinite(x) for x in values):
        raise ValueError("C08_NONFINITE_BIN")
    expected=(.55,.25,1.63,0.,0.,0.,.30,.30,.20)
    if max(abs(a-b) for a,b in zip(values,expected))>1e-8:
        raise ValueError("C08_UNEXPECTED_BIN_FRAME_OR_COLLISION")
    return {"id":"g04b_existing_gazebo_bin_collision",
            "frame_id":"base_link","center_m":values[:3],
            "box_m":values[6:],"source":"ORIGINAL_STATIC_GAZEBO_BIN",
            "geometry_unchanged":True,
            "G04B":"BLOCKED_PENDING_NATIVE_PHYSICAL_ACCEPTANCE"}
