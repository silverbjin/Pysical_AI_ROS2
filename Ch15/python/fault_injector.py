"""C21/fixture identity: declaration is NOT evidence of injection.
Mock-only contracts; no ROS publisher or physical motion API in this module.
"""
import hashlib,json
from pathlib import Path
from uuid import uuid4

def load_fixtures(path):
    raw=Path(path).read_bytes()
    data=json.loads(raw) # JSON subset of YAML; no implicit YAML coercion
    if data.get('schema')!=1 or data.get('profile')!='mock':
        raise ValueError('mock schema1 required')
    fixtures=data['fixtures']
    ids=[x['fault_id'] for x in fixtures]
    if len(ids)!=10 or set(ids)!={f'F{i:02d}' for i in range(1,11)}:
        raise ValueError('exact ten unique faults required')
    for f in fixtures:
        if (f['profile']!='mock' or type(f['seed']) is not int
            or type(f['retry_budget']) is not int
            or f['retry_budget']!=(3 if f['fault_id'] in ('F03','F06') else 0)
            or not f['required_witness'] or len(set(f['required_witness']))!=len(f['required_witness'])
            or not f['trigger']['phase'] or not f['trigger']['kind'] or not f['expected_mission_terminal']):
            raise ValueError('invalid fault contract')
    return {f['fault_id']:f for f in fixtures},hashlib.sha256(raw).hexdigest()

def new_receipt(path,fault_id):
    fixtures,sha=load_fixtures(path)
    f=fixtures[fault_id]
    return dict(run_id=uuid4().hex,fixture_sha256=sha,fault=f,source='MOCK',injection_observed=False,result='NOT_RUN')

def l0_disposition(fault_id,*,obstacle=False,ik_available=True,attitude_valid=True,battery_pct=100.,clock_valid=True):
    # Deterministic negative scenario policy, not a runtime robot controller.
    import math
    if fault_id=='F02' and obstacle is True:return 'BLOCK_OR_REPLAN'
    if fault_id=='F05' and ik_available is not True:return 'BLOCKED'
    if fault_id=='F08' and attitude_valid is not True:return 'BLOCKED'
    if fault_id=='F09' and (type(battery_pct) not in (int,float) or not math.isfinite(battery_pct) or not 20<=battery_pct<=100):return 'ABORTED'
    if fault_id=='F10' and clock_valid is not True:return 'BLOCKED'
    return 'NO_FAULT'
