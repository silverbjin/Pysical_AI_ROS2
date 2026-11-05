"""Immutable ten-slot provenance and fail-closed, stratified evaluation."""
import math
import re
import uuid
from statistics import mean
from .metrics import assess_trials,FIELDS

LEVELS=('level2_obstacles','level3_house')


def make_plan(source_sha256,scenario_hashes,*,identities=None):
    if not re.fullmatch('[0-9a-f]{64}',source_sha256):raise ValueError('source SHA256 required')
    if set(scenario_hashes)!=set(LEVELS) or any(not re.fullmatch('[0-9a-f]{64}',v) for v in scenario_hashes.values()):
        raise ValueError('both scenario SHA256 values required')
    identities=[str(uuid.uuid4()) for _ in range(10)] if identities is None else list(identities)
    if len(identities)!=10 or len(set(identities))!=10:raise ValueError('ten distinct UUIDs required')
    if any(str(uuid.UUID(i))!=i for i in identities):raise ValueError('canonical UUID required')
    return dict(schema='ch13_level23_ten_v1',source_manifest_sha256=source_sha256,
        expected=10,seed_policy='unchanged deterministic simulator setup; scheduling is not deterministic',
        slots=[dict(index=i+1,uuid=identities[i],scenario=LEVELS[i%2],scenario_sha256=scenario_hashes[LEVELS[i%2]]) for i in range(10)])


def assess_batch(plan,trials):
    canonical=make_plan(plan['source_manifest_sha256'],
        {s['scenario']:s['scenario_sha256'] for s in plan['slots']},identities=[s['uuid'] for s in plan['slots']])
    if plan!=canonical:raise ValueError('altered schedule/schema refused')
    ids=[r['uuid'] for r in trials]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate trial refused')
    supplied={r['uuid']:r for r in trials};normalized=[];missing=[];invalid=[]
    for slot in plan['slots']:
        row=supplied.get(slot['uuid'])
        if row is None:
            missing.append(slot['uuid'])
            row=dict(uuid=slot['uuid'],scenario=slot['scenario'],success=False,complete=False,**{k:None for k in FIELDS})
        else:
            row=dict(row)
            valid=(row.get('profile')=='actual' and row.get('scenario')==slot['scenario']
                and row.get('scenario_sha256')==slot['scenario_sha256']
                and row.get('source_manifest_sha256')==plan['source_manifest_sha256'])
            if row.get('success') is True:
                valid=valid and row.get('physical',{}).get('world',{}).get('result')=='PASS'
            if not valid:
                invalid.append(slot['uuid']);row.update(success=False,complete=False)
        normalized.append(row)
    unexpected=sorted(set(supplied)-{s['uuid'] for s in plan['slots']})
    result=assess_trials(normalized,10)
    result.update(missing=missing,invalid_provenance=invalid,unexpected=unexpected,
        available_trials=len(trials),scope='ten alternating attempts, five per level; not ten repeats per level',
        by_level={name:assess_trials([r for r in normalized if r['scenario']==name],5) for name in LEVELS},
        available_metrics={k:dict(count=len(values),mean=mean(values) if values else None)
            for k in FIELDS for values in [[r[k] for r in normalized if type(r.get(k)) in (int,float) and math.isfinite(r[k]) and r[k]>=0]]})
    result['checks']['provenance']=not invalid and not unexpected
    result['result']='PASS' if all(result['checks'].values()) else 'FAIL'
    return result
