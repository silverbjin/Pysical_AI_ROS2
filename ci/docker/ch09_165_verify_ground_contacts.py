#!/usr/bin/env python3
"""Parse actual Gazebo gz.msgs.Contacts text from TEST-ONLY ground sensor.

Only count contact pairs with original four named foot collisions vs ground.
Measured contact points are a slip proxy, NOT direct friction coefficients.
"""
import json
import math
from pathlib import Path
import re
import sys

raw, result_path = map(Path, sys.argv[1:])
source = raw.read_text(errors="replace")
feet = ("fr_foot", "fl_foot", "rr_foot", "rl_foot")


def blocks(text, tag):
    pattern = re.compile(r"\b" + re.escape(tag) + r"\s*\{")
    pos = 0
    while (m := pattern.search(text, pos)) is not None:
        start = m.end() - 1
        depth = 0
        end = start
        for end in range(start, len(text)):
            if text[end] == "{":
                depth += 1
            elif text[end] == "}":
                depth -= 1
                if depth == 0:
                    yield text[start+1:end]
                    pos = end + 1
                    break
        else:
            break


def nfield(text, key):
    m = re.search(r"\b" + re.escape(key) + r"\s*:\s*([-+\d.eE]+)", text)
    return float(m.group(1)) if m else None


events = {k: [] for k in feet}
all_blocks = list(blocks(source, "contact"))
for b in all_blocks:
    one = next(iter(blocks(b, "collision1")), "")
    two = next(iter(blocks(b, "collision2")), "")
    n1 = re.search(r'\bname\s*:\s*"([^"]+)"', one)
    n2 = re.search(r'\bname\s*:\s*"([^"]+)"', two)
    names = (n1.group(1) if n1 else "", n2.group(1) if n2 else "")
    if not any("ground_plane" in n for n in names):
        continue
    foot = next((f for f in feet if any(f in n for n in names)), None)
    if foot is None:
        continue
    all_forces = []
    for fblock in blocks(b, "force"):
        xyz = [nfield(fblock, axis) for axis in ("x","y","z")]
        if all(v is not None and math.isfinite(v) for v in xyz):
            all_forces.append(math.sqrt(sum(v*v for v in xyz)))
    positions = []
    for pblock in blocks(b, "position"):
        xyz = [nfield(pblock, axis) for axis in ("x","y","z")]
        if all(v is not None and math.isfinite(v) for v in xyz):
            positions.append(xyz)
    events[foot].append({
        "collisions": names,
        "max_reported_force_N": max(all_forces) if all_forces else None,
        "first_contact_point_m": positions[0] if positions else None,
    })

rows = {}
for foot in feet:
    data = events[foot]
    positive = [e["max_reported_force_N"] for e in data
                if e["max_reported_force_N"] is not None
                and e["max_reported_force_N"] > 1e-4]
    pos = [e["first_contact_point_m"] for e in data
           if e["first_contact_point_m"] is not None]
    spread = None
    if len(pos) >= 2:
        spread = math.hypot(max(p[0] for p in pos)-min(p[0] for p in pos),
                            max(p[1] for p in pos)-min(p[1] for p in pos))
    rows[foot] = {
        "ground_contact_records": len(data),
        "reported_force_samples_positive": len(positive),
        "max_reported_force_N": max(positive) if positive else None,
        "contact_xy_extents_diagonal_m": spread,
        "example_collision_pair": data[0]["collisions"] if data else None,
        "sample_points": pos[:4],
    }

all_seen = all(rows[f]["ground_contact_records"] >= 3 for f in feet)
all_forces = all(rows[f]["reported_force_samples_positive"] >= 1 for f in feet)
status = "PASS" if all_seen and all_forces else "FAIL"
receipt = {
    "status": status, "issue": 165,
    "scope": "original_Ch09_stand_four_ground_contacts_test_only_Gazebo_contact_sensor",
    "raw_text_bytes": raw.stat().st_size,
    "total_contact_blocks": len(all_blocks),
    "started_capture_after_original_6s_stand_ramp": True,
    "four_feet_ground_contact_events": all_seen,
    "four_feet_positive_actual_contact_force": all_forces,
    "per_foot": rows,
    "not_run": ["measured static/kinetic friction coefficient",
                "full ground slip velocity/traction",
                "independent 3x cold starts", "GUI", "hardware", "Ch10"],
}
result_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print("CH09_165_ACTUAL_FOUR_FOOT_GROUND_CONTACT_" + status +
      " " + json.dumps({k:v for k,v in receipt.items() if k!="per_foot"}),
      flush=True)
sys.exit(0 if status=="PASS" else 1)
