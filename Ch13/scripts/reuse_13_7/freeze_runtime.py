"""Immutable 13.7 source set; never rewrite the historical 13.6 freeze."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Ch13/scripts/reuse_13_6'))
import freeze_runtime as previous


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    paths=previous.sources()
    for folder in [ROOT/'Ch13/scripts/reuse_13_7',ROOT/'Ch13/ros2_ws/src/ch13_mission_orchestration',ROOT/'Ch13/config']:
        for p in folder.rglob('*'):
            if p.is_file() and not any(x in p.parts for x in ('__pycache__','.pytest_cache')):
                paths[p.relative_to(ROOT).as_posix()]=digest(p)
    return dict(sorted(paths.items()))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['write','verify']);ap.add_argument('manifest',type=Path)
    args=ap.parse_args();source=sources()
    if args.mode=='write':
        if args.manifest.exists():raise ValueError('immutable freeze; choose new filename')
        assets=json.loads((ROOT/'Ch13/dependencies/section_13_5_reuse.lock.json').read_text())['files']
        args.manifest.write_text(json.dumps(dict(revision=args.manifest.stem,source=source,assets=assets),indent=2)+'\n')
    data=json.loads(args.manifest.read_text());assert data['source']==source,'source mismatch'
    assets=ROOT.parent/'upstream-iit-locomanipulation-d010212'
    assert all(digest(assets/f['path'])==f['sha256'] for f in data['assets']),'asset mismatch'
    print(json.dumps(dict(result='PASS',revision=data['revision'],sources=len(source),assets=len(data['assets']),sha256=digest(args.manifest))))


if __name__=='__main__':main()
