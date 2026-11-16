"""C12: rotate only original solid, physically present test bin +0.35rad."""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
YAW=.35
START="0.55 0.25 1.63 0 0 0"
END="0.55 0.25 1.63 0 0 0.35"

def rotate_bin(world_path,receipt_path):
 p=Path(world_path);prior=p.read_bytes();root=ET.fromstring(prior)
 model=root.find("./world[@name='book_camera']/model[@name='g04_bin_support']")
 if model is None or model.findtext("static")!="true":
  raise ValueError("C12_ORIGINAL_STATIC_BIN_MISSING")
 pose=model.find("pose");link=model.find("./link[@name='bin_support']")
 box=(link.find("./collision[@name='bin_collision']") if link is not None else None)
 if (pose is None or pose.text.strip()!=START or box is None
     or box.findtext("./geometry/box/size","").strip()!="0.30 0.30 0.20"
     or link.find("pose") is not None or box.find("pose") is not None):
  raise ValueError("C12_ORIGINAL_BIN_CENTER_SHAPE_OR_ORIENTATION_CHANGED")
 snapshot=ET.tostring(root);pose.text=END;updated=ET.tostring(root)
 pose.text=START
 if ET.tostring(root)!=snapshot:
  raise ValueError("C12_UNRELATED_WORLD_MUTATION")
 pose.text=END
 if ET.tostring(root)!=updated:
  raise ValueError("C12_WORLD_DIFF_NOT_SINGLE_FIELD")
 p.write_bytes(updated)
 info={"only_change":"real_bin_model_yaw_0_to_0.35_rad",
   "bin_world_center_m":[.55,.25,1.63],"bin_dimensions_m":[.30,.30,.20],
   "bin_top_m":1.73,"original_xml_sha256":hashlib.sha256(prior).hexdigest(),
   "rotated_xml_sha256":hashlib.sha256(updated).hexdigest(),
   "native_collision_enabled":True,"fake_object_attachment":False,
   "G04B":"BLOCKED_PENDING_FULL_NATIVE_PHYSICAL_RUN"}
 Path(receipt_path).write_text(json.dumps(info,indent=2)+"\n")
 return info

if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--world",required=True)
 a.add_argument("--receipt",required=True);n=a.parse_args()
 print(json.dumps(rotate_bin(n.world,n.receipt),sort_keys=True))
