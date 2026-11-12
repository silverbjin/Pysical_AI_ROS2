#!/usr/bin/env python3
"""Validate the actual SLAM map saver outputs and prevent false success on logs.

Reads only the two files written by /slam_toolbox/save_map, and checks the PGM
pixels for observed/nonunknown cells (not a mapping accuracy assessment).
"""
import hashlib
import json
from pathlib import Path
import sys
import yaml

outdir=Path(sys.argv[1]).resolve()
name=sys.argv[2]
assert name=="book_ch11_map"
yaml_path=outdir/(name+".yaml")
assert yaml_path.is_file(), "Missing saved map YAML: "+str(yaml_path)
config=yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
assert isinstance(config,dict), "Malformed map YAML"
assert float(config.get("resolution",0))>0, "Invalid resolution"
assert len(config.get("origin",[]))>=3, "Missing origin"
image_name=config.get("image")
assert isinstance(image_name,str), "Map YAML lacks image"
img=(yaml_path.parent/image_name).resolve()
assert img.parent==outdir, "Map image is outside evidence directory"
assert img.is_file(), "Map image not written"
payload=img.read_bytes()
assert payload.startswith(b"P5"), "Expected binary PGM from slam_toolbox"
# PGM ASCII header separated by whitespace; skip #-comments.
cursor=0;tokens=[]
while len(tokens)<4:
    while cursor<len(payload) and payload[cursor] in b" \r\n\t":cursor+=1
    if cursor<len(payload) and payload[cursor]==35:
        while cursor<len(payload) and payload[cursor]!=10:cursor+=1
        continue
    end=cursor
    while end<len(payload) and payload[end] not in b" \r\n\t":end+=1
    assert end>cursor,"Truncated PGM header"
    tokens.append(payload[cursor:end])
    cursor=end
assert tokens[0]==b"P5", "Unexpected map image format"
width,height,maxval=map(int,tokens[1:])
assert width>=10 and height>=10 and maxval==255
assert cursor<len(payload) and payload[cursor] in b" \r\n\t", "PGM header separator missing"
# Standard P5 binary pixels start immediately after one whitespace delimiter.
pixels=payload[cursor+1:]
assert len(pixels)==width*height, f"PGM payload {len(pixels)} != {width*height}"
# Standard ROS map saver: unknown 205, free 254, occupied 0.
unknown=pixels.count(205)
observed=len(pixels)-unknown
assert observed>40, f"Map has insufficient observed cells: {observed}"
evidence={"image_name":img.name,"width":width,"height":height,
          "resolution_m":float(config["resolution"]),
          "image_bytes":len(payload),"observed_nonunknown_cells":observed,
          "unknown_cells":unknown,
          "yaml_sha256":hashlib.sha256(yaml_path.read_bytes()).hexdigest(),
          "image_sha256":hashlib.sha256(payload).hexdigest(),
          "map_origin":config.get("origin"),
          "not_run":["repeat map saving after long exploration",
                     "ground-truth location accuracy","loop closure",
                     "load_map and navigation","GUI"]}
result={"chapter":"Ch11","scope":"actual slam_toolbox SaveMap service file round-trip",
        "status":"PASS","whole_chapter_accepted":False,"evidence":evidence}
(outdir/"map_save_verdict.json").write_text(
    json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print("CH11_MAP_SAVE_FILES_AND_PIXELS_PASS "+json.dumps(evidence),flush=True)
