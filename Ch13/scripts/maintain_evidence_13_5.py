#!/usr/bin/env python3
"""Preview/apply closed-trial retention. No simulator or privileged operation."""
import argparse
import json
import os
from pathlib import Path

from evidence_retention_13_5 import bulk,maintain_trials


def quiescent():
    if not Path('/proc').is_dir():return
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:args=(entry/'cmdline').read_bytes().split(b'\0');name=Path(os.fsdecode(args[0])).name
        except (OSError,IndexError):continue
        if name in ('mujoco_ros2_control','navigation_evidence_recorder','gz','gz-sim-server') or (
                name.startswith('python') and any(b'run_navigation_13_5.py' in arg for arg in args[1:])):
            raise RuntimeError('runtime is live; evidence maintenance refused')


def preview(root,pins=()):
    items=[];latest={}
    pin_file=root/'retention_pins.json'
    if pin_file.is_symlink():raise ValueError('pin symlink refused')
    persistent=json.loads(pin_file.read_text()).get('trials',{}) if pin_file.exists() else {}
    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.is_symlink():continue
        try:result=json.loads((path/'result.json').read_text());closed=json.loads((path/'teardown.json').read_text())
        except (OSError,ValueError):continue
        if closed.get('parent_reaped') is not True or closed.get('residual_live_pids')!=[]:continue
        marker=path/'retention.json'
        if marker.exists() and not json.loads(marker.read_text()).get('raw_complete'):continue
        key=(result.get('engine'),result.get('gate'),result.get('scenario'),result.get('status'))
        rank=(path/'result.json').stat().st_mtime_ns
        if key not in latest or rank>latest[key][0]:latest[key]=(rank,path.name)
        items.append(path)
    keep={row[1] for row in latest.values()}|set(pins)|set(persistent)
    return dict(mode='dry_run',representatives=sorted(keep),retire=[path.name for path in items if path.name not in keep],
        reclaimable_raw_bytes=sum(file.stat().st_size for path in items if path.name not in keep
            for file in path.rglob('*') if file.is_file() and not file.is_symlink() and bulk(file.name,file.stat().st_size)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,help='one owned evidence directory containing completed trial subdirectories')
    parser.add_argument('--apply',action='store_true');parser.add_argument('--pin',action='append',default=[])
    args=parser.parse_args();root=Path(args.root).resolve(strict=True);quiescent()
    value=maintain_trials(root,pins=args.pin) if args.apply else preview(root,args.pin)
    print(json.dumps(value,indent=2))


if __name__=='__main__':main()
