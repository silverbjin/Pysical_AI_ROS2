import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1]/'scripts/evidence_retention_13_5.py'
spec = importlib.util.spec_from_file_location('retention', SCRIPT)
retention = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retention)


def test_retention_contract_exists():
    assert hasattr(retention, 'compact_trial'), 'closed trials need bounded retention, not another full archive'


def closed_trial(root, status='FAIL'):
    root.mkdir()
    (root/'result.json').write_text(json.dumps(dict(status=status,engine='mujoco',gate='G2',
        errors=['original failure'],checks={'support':False})))
    (root/'teardown.json').write_text(json.dumps(dict(parent_reaped=True,residual_live_pids=[],
        finalization_complete=True)))
    (root/'source_manifest.json').write_text('{"files":{"example.py":"oldhash"}}')
    return root


def test_nonrepresentative_keeps_verdict_summary_and_sample(tmp_path):
    root=closed_trial(tmp_path/'trial')
    original=(root/'result.json').read_bytes()
    raw=root/'observations.jsonl'
    with raw.open('w') as stream:
        for i in range(100):
            stream.write(json.dumps(dict(kind='frame',value=dict(wall_ns=i*20_000_000,
                ros_ns=i*20_000_000,stage='forward',crawl={'state':'CRAWL'},
                samples={'body':{'data':{'position':[i,0,0]}}})))+'\n')
    digest=hashlib.sha256(raw.read_bytes()).hexdigest()
    report=retention.compact_trial(root,allowed_root=tmp_path,representative=False,minimum_bytes=1)
    assert (root/'result.json').read_bytes()==original
    assert not raw.exists() and report['removed_bytes']>0
    rows=[json.loads(line) for line in (root/'retained_samples/observations.jsonl').read_text().splitlines()]
    assert 2<=len(rows)<=5 and rows[-1]['value']['wall_ns']>0
    assert all(b['value']['wall_ns']-a['value']['wall_ns']>=500_000_000 for a,b in zip(rows,rows[1:]))
    assert report['removed'][0]['sha256']==digest
    assert json.loads((root/'retention.json').read_text())['raw_complete'] is False
    assert retention.compact_trial(root,allowed_root=tmp_path,representative=False,minimum_bytes=1)['already_applied']


def test_representative_and_unclosed_trials_cannot_be_thinned(tmp_path):
    root=closed_trial(tmp_path/'representative')
    (root/'frames.json').write_text('[1,2,3]')
    retention.compact_trial(root,allowed_root=tmp_path,representative=True,minimum_bytes=1)
    assert (root/'frames.json').read_text()=='[1,2,3]'
    root=closed_trial(tmp_path/'unclosed')
    (root/'teardown.json').write_text('{"parent_reaped":false,"residual_live_pids":[42]}')
    (root/'frames.json').write_text('[1,2,3]')
    with pytest.raises(ValueError,match='cleanup'):
        retention.compact_trial(root,allowed_root=tmp_path,representative=False,minimum_bytes=1)
    assert (root/'frames.json').exists()


def test_symlink_and_path_escape_refused(tmp_path):
    safe=tmp_path/'safe';safe.mkdir()
    outside=closed_trial(tmp_path/'outside')
    with pytest.raises(ValueError,match='outside'):
        retention.compact_trial(outside,allowed_root=safe,representative=False)
    root=closed_trial(safe/'trial');(root/'frames.json').symlink_to(outside/'result.json')
    with pytest.raises(ValueError,match='symlink'):
        retention.compact_trial(root,allowed_root=safe,representative=False)


def test_archive_keeps_sources_and_result_and_records_raw_identity(tmp_path):
    target=tmp_path/'old.zip'
    with zipfile.ZipFile(target,'w') as output:
        output.writestr('sources/Ch13/example.py','print(1)')
        output.writestr('evidence/trial/result.json','{"status":"FAIL"}')
        output.writestr('evidence/trial/observations.jsonl','large raw content')
    report=retention.compact_archive(target,allowed_root=tmp_path,minimum_bytes=1)
    assert not target.exists()
    with zipfile.ZipFile(tmp_path/'old.metadata.zip') as source:
        assert source.read('sources/Ch13/example.py')==b'print(1)'
        assert source.read('evidence/trial/result.json')==b'{"status":"FAIL"}'
        assert 'evidence/trial/observations.jsonl' not in source.namelist()
    assert report['original_sha256'] and report['removed_members'][0]['name'].endswith('observations.jsonl')


def test_storage_and_time_budget_fail_closed(tmp_path):
    root=tmp_path/'trial';root.mkdir();(root/'observations.cdr').write_bytes(b'a'*10)
    budget=retention.EvidenceBudget(root,raw_bytes=8,working_bytes=100,wall_seconds=10,started=1.)
    with pytest.raises(RuntimeError,match='storage_budget'):
        budget.check(now=2.)
    (root/'observations.cdr').unlink()
    with pytest.raises(RuntimeError,match='time_budget'):
        budget.check(now=11.1)
    assert retention.EvidenceBudget(root,raw_bytes=8,working_bytes=100,wall_seconds=10,started=1.).check(now=2.)['passed']


def test_previous_representative_can_retire_but_summary_cannot_be_promoted(tmp_path):
    root=closed_trial(tmp_path/'old')
    (root/'frames.json').write_text('[1,2,3]')
    retention.compact_trial(root,allowed_root=tmp_path,representative=True,minimum_bytes=1)
    result=retention.compact_trial(root,allowed_root=tmp_path,representative=False,minimum_bytes=1)
    assert not (root/'frames.json').exists() and not result['raw_complete']
    with pytest.raises(ValueError,match='promote'):
        retention.compact_trial(root,allowed_root=tmp_path,representative=True,minimum_bytes=1)


def test_rotating_latest_per_engine_gate_outcome_and_pin(tmp_path):
    for name,status in (('old','FAIL'),('new','FAIL'),('passed','PASS')):
        root=closed_trial(tmp_path/name,status);(root/'frames.json').write_text('[1,2,3]')
    report=retention.maintain_trials(tmp_path,minimum_bytes=1)
    assert not (tmp_path/'old/frames.json').exists()
    assert (tmp_path/'new/frames.json').exists() and (tmp_path/'passed/frames.json').exists()
    assert report['representatives']==['new','passed']


def test_record_summary_never_counts_as_full_replay_and_sample_is_bounded(tmp_path):
    source=tmp_path/'input.jsonl'
    with source.open('w') as output:
        for i in range(200):
            output.write(json.dumps(dict(kind='frame',value=dict(wall_ns=i*500_000_000,ros_ns=i,
                position=[i]*3,stage='stand')))+'\n')
    value=retention.sample_jsonl(source,tmp_path/'samples.jsonl',max_bytes=1024)
    assert value['bytes']<=1024 and 'not_full_replay' in value['scope']


def test_open_original_cannot_be_retired_even_with_an_old_closed_verdict(tmp_path):
    if not Path('/proc/self/fd').is_dir():pytest.skip('Linux ownership inspection')
    root=closed_trial(tmp_path/'trial');raw=root/'frames.json';raw.write_text('[1,2,3]')
    process=subprocess.Popen([sys.executable,'-c',
        'import sys; f=open(sys.argv[1]); print("ready",flush=True); sys.stdin.readline(); f.close()',str(raw)],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    try:
        assert process.stdout.readline().strip()=='ready'
        with pytest.raises(ValueError,match='opened'):
            retention.compact_trial(root,allowed_root=tmp_path,representative=False,minimum_bytes=1)
        assert raw.exists()
    finally:
        process.stdin.write('stop\n');process.stdin.flush();process.wait(timeout=5)
        process.stdin.close();process.stdout.close()


def test_pin_survives_later_automatic_rotation(tmp_path):
    for name in ('baseline','current'):
        root=closed_trial(tmp_path/name);(root/'frames.json').write_text('[1,2,3]')
    retention.maintain_trials(tmp_path,pins=['baseline'],minimum_bytes=1)
    retention.maintain_trials(tmp_path,minimum_bytes=1)
    assert (tmp_path/'baseline/frames.json').exists()
    assert 'baseline' in json.loads((tmp_path/'retention_pins.json').read_text())['trials']
