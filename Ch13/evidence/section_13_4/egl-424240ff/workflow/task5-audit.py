"""Audit execution/evidence completeness, NOT product acceptance."""
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID

root = Path(os.environ['CH13_EGL_EVIDENCE'])
expected = {'static-off','static-on','delay-on'} | {f'm{rate}{suffix}' for rate in (10,15) for suffix in 'abc'}
expected |= {engine+'-'+scenario for engine in ('mujoco','gazebo') for scenario in ('cup','images','tf','joints')}
expected |= {'gazebo-static','gazebo-delay','gazebo-tracking'}
progress = [json.loads(v) for v in (root/'matrix-progress.jsonl').read_text().splitlines()]
assert len(progress) == len(expected) == 20
assert {v['label'] for v in progress} == expected
assert len({v['run_id'] for v in progress}) == 20
frozen = None
artifacts = 0
for trial in progress:
    assert trial['cleanup_confirmed'] and trial['live_engines_after'] == []
    folder = root/trial['label']
    result = json.loads((folder/'result.json').read_text())
    assert str(UUID(result['run_id'])) == trial['run_id']
    assert result['status'] == trial['status'] and result['status'] in ('PASS','FAIL')
    assert result['source_head'] == '09b057465da50ffcf892c30e2e8f7e9f516ab953'
    snapshot = json.loads((folder/'source_snapshot.json').read_text())['files']
    if frozen is None:
        frozen = snapshot
    assert snapshot == frozen, trial['label']+' runtime source changed during matrix'
    assert result['cleanup'] and all(v['residual_live_pids'] == [] for v in result['cleanup'])
    for artifact in result['artifacts']:
        path = (folder/artifact['path']).resolve(strict=True)
        assert path.is_relative_to(folder.resolve())
        assert path.stat().st_size == artifact['size'] > 0
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact['sha256']
        artifacts += 1
    trace = result.get('trace_analysis')
    if result.get('trace_enabled'):
        assert (folder/'trace.jsonl').is_file() and (folder/'trace_summary.json').is_file()
        assert trace is not None
        for line in (folder/'trace.jsonl').read_text().splitlines():
            assert json.loads(line)['record']['run_id'] == result['run_id']
legacy = [json.loads(v) for v in (root/'legacy-progress.jsonl').read_text().splitlines()]
assert legacy and legacy[0]['label'] == 'legacy_mujoco'
assert len(legacy) == 2 or legacy[0]['status'] == 'FAIL'
assert len(legacy) <= 2
if len(legacy) == 2:
    assert legacy[1]['label'] == 'legacy_gazebo'
for entry in legacy:
    assert entry['cleanup_confirmed']
    folder = root/entry['label']
    result = json.loads((folder/'result.json').read_text())
    assert result['status'] == entry['status']
    for artifact in result['artifacts']:
        path = (folder/artifact['path']).resolve(strict=True)
        assert path.is_relative_to(folder.resolve())
        assert path.stat().st_size == artifact['size'] > 0
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact['sha256']
        artifacts += 1
print(json.dumps(dict(execution_evidence_audit='PASS',native_trials=20,legacy_trials=len(legacy),
    artifact_hashes_verified=artifacts,native_pass=sum(v['status']=='PASS' for v in progress),
    native_fail=sum(v['status']=='FAIL' for v in progress),product_acceptance='FAIL',
    note='Completeness/integrity PASS does not turn failed product trials into PASS.')))
