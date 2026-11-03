"""Freeze/verify this revision, independently of unchanged 13.5 v3 evidence."""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
PACKAGES=('ch13_reuse_wire','ch13_navigation_reuse','integrated_robot_vision',
          'ch13_manipulation_reuse','ch13_piper_moveit_config','ch13_manipulation_planner')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    paths=[]
    for folder in [*(ROOT/'Ch13/ros2_ws/src'/p for p in PACKAGES),ROOT/'Ch13/scripts/reuse_13_5',ROOT/'Ch13/scripts/reuse_13_6']:
        paths.extend(p for p in folder.rglob('*') if p.is_file() and not any(s in p.parts for s in ('__pycache__','.pytest_cache')))
    paths.extend(ROOT/'Ch13/dependencies'/p for p in ('section_13_5_reuse.lock.json','section_13_5_edu_stop_v2.json',
                 'section_13_6_control_v1.json','section_13_6_control_v2.json','section_13_6_pick_contract_v1.json','section_13_6_pick_contract_v2.json','section_13_6_pick_contract_v3.json','section_13_6_pick_contract_v4.json','section_13_6_pick_contract_v5.json','section_13_6_pick_contract_v6.json'))
    return {p.relative_to(ROOT).as_posix():digest(p) for p in sorted(set(paths))}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['write','verify']);parser.add_argument('manifest',type=Path)
    parser.add_argument('--revision',default='13_6_manipulation_acceptance_v1')
    args=parser.parse_args()
    if args.mode=='write':
        if args.manifest.exists():raise ValueError('freeze is immutable; use a new revision filename')
        legacy=ROOT/'Ch13/dependencies/section_13_5_reuse.lock.json'
        data=dict(revision=args.revision,created_utc=datetime.now(timezone.utc).isoformat(),
                  source=sources(),asset_manifest_sha256=digest(legacy),
                  assets=json.loads(legacy.read_text())['files'],
                  meaning='source and original assets; installed code/model/ELF audited separately before each run')
        args.manifest.parent.mkdir(parents=True,exist_ok=True);args.manifest.write_text(json.dumps(data,indent=2)+'\n')
    data=json.loads(args.manifest.read_text());actual=sources()
    assert actual==data['source'],'runtime source set or hash changed after freeze'
    assets=ROOT.parent/'upstream-iit-locomanipulation-d010212'
    assert all(digest(assets/f['path'])==f['sha256'] for f in data['assets']),'original asset mismatch'
    print(json.dumps(dict(result='PASS',revision=data['revision'],source_files=len(actual),assets=len(data['assets']),
                          manifest_sha256=digest(args.manifest)),indent=2))


if __name__=='__main__':main()
