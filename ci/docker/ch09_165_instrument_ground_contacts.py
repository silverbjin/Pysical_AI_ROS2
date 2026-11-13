#!/usr/bin/env python3
"""Test-only Gazebo ground contact sensor for all four original Ch09 feet."""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

source, destination, manifest = map(Path, sys.argv[1:])
original = source.read_bytes()
root = ET.fromstring(original)
world = root.find("./world[@name='my_empty_world']")
if world is None:
    raise RuntimeError("CH09_165_WORLD_NOT_ORIGINAL")
assert not any(p.get("filename") == "gz-sim-contact-system" for p in world.findall("plugin"))
ground = world.find("./model[@name='ground_plane']/link[@name='link']")
assert ground is not None and ground.find("./collision[@name='collision']") is not None
mu = ground.find("./collision[@name='collision']/surface/friction/ode")
assert mu is not None and mu.findtext("mu") == mu.findtext("mu2") == "1.0"
ET.SubElement(world, "plugin", {"filename": "gz-sim-contact-system",
                                "name": "gz::sim::systems::Contact"})
sensor = ET.SubElement(ground, "sensor",
                       {"name": "book_ch09_ground_contact", "type": "contact"})
for k,v in (("always_on","true"), ("update_rate","10"),
            ("topic","/book_ch09/ground_contacts")):
    ET.SubElement(sensor,k).text=v
ET.SubElement(ET.SubElement(sensor,"contact"),"collision").text="collision"
destination.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))
manifest.write_text(json.dumps({
    "original_world_sha256": hashlib.sha256(original).hexdigest(),
    "world_fixture": "TEST_ONLY_SENSOR_ADDED",
    "original_source_modified": False,
    "contact_topic": "/book_ch09/ground_contacts",
    "source_ground_mu1": 1.0, "source_ground_mu2": 1.0,
    "friction_coefficient_dynamically_measured": False,
    "ch10": "HOLD"},indent=2)+"\n")
print("CH09_165_TEST_ONLY_GROUND_CONTACT_WORLD_READY",flush=True)
