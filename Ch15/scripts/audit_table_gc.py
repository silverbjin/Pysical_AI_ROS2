#!/usr/bin/env python3
"""Read-only audit of actual Ch15 native receipt ZIP. No ROS or motion authority."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def audit(path, expected_sha=None):
    with Path(path).open('rb') as f:
        archive_sha = hashlib.file_digest(f, 'sha256').hexdigest()
    if expected_sha is not None and archive_sha != expected_sha:
        raise ValueError('archive SHA256 mismatch')
    with zipfile.ZipFile(path) as z:
        manifest = z.read('sha256sums.txt').decode().splitlines()
        verified = set()
        for line in manifest:
            digest, name = line.split(maxsplit=1)
            name = name.lstrip('*').removeprefix('./')
            if name in verified or hashlib.sha256(z.read(name)).hexdigest() != digest:
                raise ValueError('member SHA256 mismatch or duplicate: '+name)
            verified.add(name)
        if len(z.namelist()) != len(set(z.namelist())) or set(z.namelist()) != verified | {'sha256sums.txt'}:
            raise ValueError('unexpected archive members')
        def data(name):
            return json.loads(z.read('case/native/'+name+'.json'))
        def rows(name):
            return [json.loads(line) for line in z.read('case/native/'+name+'.jsonl').splitlines()]
        engine = data('engine'); observed = rows('engine_observations')
        if len(observed)<2:raise ValueError('insufficient actual engine observations')
        gaps=[]
        for a,b in zip(observed,observed[1:]):
            if b['wall']<=a['wall'] or b['sim_s']<=a['sim_s']:raise ValueError('nonmonotonic sample clock')
            gaps.append(dict(start_sim_s=a['sim_s'],end_sim_s=b['sim_s'],start_wall=a['wall'],end_wall=b['wall'],wall_s=b['wall']-a['wall']))
        events=[]
        for event in engine.get('gc_timing',{}).get('events',[]):
            if event['generation']!=2:continue
            overlaps=[]
            for gap in gaps:
                overlap=min(event['end_wall'],gap['end_wall'])-max(event['start_wall'],gap['start_wall'])
                if overlap>0:overlaps.append({**gap,'overlap_s':overlap})
            events.append({'gc':event,'overlaps':overlaps})
        policy=data('gc_policy_receipt') if 'case/native/gc_policy_receipt.json' in verified else None
        return dict(scope='actual archived timing; no causal guarantee beyond measured overlaps',archive_sha256=archive_sha,verified_members=len(verified),engine_samples=len(observed),generation2_counts=engine.get('gc_timing',{}).get('counts',{}).get('2',0),gaps_over_100ms=[g for g in gaps if g['wall_s']>.1],generation2_events=events,policy=policy)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('zip');p.add_argument('--sha256');a=p.parse_args()
    print(json.dumps(audit(a.zip,a.sha256),indent=2,allow_nan=False))
