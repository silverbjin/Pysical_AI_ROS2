"""13.8 immutable source/asset manifest, separate from prior chapter evidence."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    spec=importlib.util.spec_from_file_location('bt_source_freeze',ROOT/'Ch13/scripts/reuse_13_7/freeze_runtime.py')
    previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
    paths=previous.sources()
    for folder in (ROOT/'Ch13/scripts/reuse_13_8',ROOT/'Ch13/ros2_ws/src/ch13_system_validation'):
        for path in folder.rglob('*'):
            if path.is_file() and not any(p in path.parts for p in ('__pycache__','.pytest_cache')):
                paths[path.relative_to(ROOT).as_posix()]=digest(path)
    return dict(sorted(paths.items()))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['write','verify']);ap.add_argument('manifest',type=Path)
    args=ap.parse_args()
    if args.mode=='write':
        if args.manifest.exists():raise ValueError('immutable source freeze; choose a new filename')
        args.manifest.parent.mkdir(parents=True,exist_ok=True)
        assets=json.loads((ROOT/'Ch13/dependencies/section_13_5_reuse.lock.json').read_text())['files']
        args.manifest.write_text(json.dumps(dict(revision=args.manifest.stem,source=sources(),assets=assets),indent=2)+'\n')
    data=json.loads(args.manifest.read_text());assert data['source']==sources(),'runtime source mismatch'
    assets=ROOT.parent/'upstream-iit-locomanipulation-d010212'
    assert all(digest(assets/f['path'])==f['sha256'] for f in data['assets']),'asset mismatch'
    print(json.dumps(dict(result='PASS',sources=len(data['source']),assets=len(data['assets']),sha256=digest(args.manifest))))


if __name__=='__main__':main()
