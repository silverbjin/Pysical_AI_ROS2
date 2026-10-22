"""Archive generated JUnit bytes outside build discovery; do not edit raw tests."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

build = Path(os.environ["CH13_EGL_BUILD"]).resolve()
output = Path(os.environ["CH13_EGL_EVIDENCE"]).resolve()/sys.argv[1]
output.mkdir(exist_ok=False)
rows = []
for path in sorted(build.rglob("*.xml")):
    if "test_results" not in path.parts and path.name != "pytest.xml":
        continue
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        continue
    if root.tag not in ("testsuites", "testsuite"):
        continue
    target = output/f"p{len(rows):03d}.xml"
    shutil.copyfile(path, target)
    rows.append(dict(path=str(path.relative_to(build)), archived=target.name,
                     sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                     size=target.stat().st_size, counts=root.attrib))
(output/"index.json").write_text(json.dumps(rows, indent=2)+"\n")
print(json.dumps(dict(archived=len(rows), output=str(output))))
