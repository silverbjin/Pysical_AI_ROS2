"""Generate a platform-specific hash lock from resolved wheel bytes; no install."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from email.parser import BytesParser


def make_lock(wheelhouse: Path, out: Path):
    rows = {}
    details = []
    for path in sorted(wheelhouse.glob("*.whl")):
        with ZipFile(path) as wheel:
            all_metadata = [x for x in wheel.namelist() if x.endswith(".dist-info/METADATA")]
            # A wheel can contain vendored distributions below its own package.
            # Only the wheel's top-level dist-info belongs to this distribution.
            matches = [x for x in all_metadata if x.count("/") == 1]
            if len(all_metadata) != len(matches):
                print(f"vendored metadata ignored: {path.name}: {sorted(set(all_metadata) - set(matches))}")
            if len(matches) != 1:
                raise ValueError(f"Invalid root wheel metadata: {path.name}: {matches}")
            meta = BytesParser().parsebytes(wheel.read(matches[0]))
        name, version = meta["Name"], meta["Version"]
        if not name or not version:
            raise ValueError(f"Missing metadata: {path.name}")
        key = name.lower().replace("_", "-").replace(".", "-")
        if key in rows:
            raise ValueError(f"Ambiguous resolved wheel: {key}")
        with path.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        rows[key] = f"{name}=={version} --hash=sha256:{digest}"
        details.append({"name": name, "version": version, "wheel": path.name,
                        "sha256": digest, "license_metadata": meta.get("License-Expression") or meta.get("License"),
                        "license_classifiers": [x for x in meta.get_all("Classifier", []) if x.startswith("License ::")]})
    if not rows or not {"torch", "torchvision", "numpy", "onnx", "onnxruntime", "ultralytics"} <= rows.keys():
        raise ValueError("Incomplete CPU wheelhouse")
    out.mkdir(parents=True, exist_ok=True)
    (out / "cpu.candidate.lock.txt").write_text("\n".join(rows[k] for k in sorted(rows)) + "\n")
    (out / "wheel_manifest.json").write_text(json.dumps(details, indent=2) + "\n")
    return len(rows)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("wheelhouse", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    print("locked_wheels", make_lock(a.wheelhouse, a.output))
