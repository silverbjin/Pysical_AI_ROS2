"""Read-only acceptance audit; derived output never changes a native verdict."""
import hashlib
import json
from pathlib import Path
import sys

root = (Path(sys.argv[1]).resolve() if len(sys.argv) > 1
        else Path(__file__).resolve().parent/'final')
frozen = json.loads((root/'frozen-source.json').read_text())
legacy_root = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else root
supplement = None
retained_legacy_failures = []
if legacy_root != root:
    supplement = json.loads((legacy_root/'frozen-source.json').read_text())
    before, after = frozen['snapshot']['files'], supplement['snapshot']['files']
    assert before.keys() <= after.keys()
    assert {p for p in after if before.get(p) != after[p]} == {
        'Ch13/scripts/verify_architecture_13_3.py', 'Ch13/tests/test_architecture_probe_time.py'}
    assert supplement['installed'] == frozen['installed']
    assert json.loads((legacy_root/'after-audit.json').read_text())['status'] == 'PASS'
    for folder in root.glob('legacy_*'):
        if folder.is_dir() and (folder/'result.json').is_file():
            result = json.loads((folder/'result.json').read_text())
            retained_legacy_failures.append(dict(label=folder.name, status=result['status'],
                run_id=result['run_id'], path=str(folder),
                native_result=json.loads((folder/'native/result.json').read_text())))
    assert len(retained_legacy_failures) == 1 and retained_legacy_failures[0]['status'] == 'FAIL'
progress = [json.loads(line) for line in (root/'matrix-progress.jsonl').read_text().splitlines()]
expected = {'static-off', 'static-on', 'delay-on', 'gazebo-static', 'gazebo-delay'}
expected |= {f'm{rate}{suffix}' for rate in (10, 15) for suffix in 'abc'}
expected |= {f'{engine}-{suffix}' for engine in ('mujoco', 'gazebo')
             for suffix in ('cup', 'images', 'tf', 'joints')}
expected |= {'gazebo-tracking-'+suffix for suffix in 'abc'}
assert len(progress) == len(expected) == 22
assert {item['label'] for item in progress} == expected
assert all(item['status'] == 'PASS' and item['returncode'] == 0
           and item['cleanup_confirmed'] and not item['live_engines_after'] for item in progress)
rows = []
for item in progress:
    folder = root/item['label']
    result = json.loads((folder/'result.json').read_text())
    source = json.loads((folder/'source_snapshot.json').read_text())
    assert source['files'] == frozen['snapshot']['files']
    assert result['status'] == 'PASS' and not result['errors']
    assert all(result['checks'].get(key) is True for key in result['required_checks'])
    for artifact in result['artifacts']:
        data = (folder/artifact['path']).read_bytes()
        assert len(data) == artifact['size']
        assert hashlib.sha256(data).hexdigest() == artifact['sha256'], (item['label'], artifact['path'])
    assert result['runtime_stop']['confirmed']
    assert all(not entry['forced_cleanup'] and not entry['residual_live_pids']
               for entry in result['cleanup'])
    if result['engine'] == 'gazebo':
        pause = result['gazebo_quiescence']
        assert pause['confirmed'] and result['gazebo_native_stop']['exited']
        assert result['runtime_stop']['finished_ns'] <= pause['started_ns']
    row = dict(label=item['label'], run_id=result['run_id'], engine=result['engine'],
               scenario=result['scenario'], checks=result['checks'],
               result_sha256=hashlib.sha256((folder/'result.json').read_bytes()).hexdigest())
    for name in ('geometry', 'tracking_metrics', 'recognition', 'fault'):
        if name in result:
            row[name] = result[name]
    observation = json.loads((folder/'observations.json').read_text())
    events = {}
    for state in observation.get('tracking', []):
        for event in state.get('owner', {}).get('events', []):
            key = (event['uuid'], event['event'], event['wall'])
            events[key] = event
    commands = {command['goal_uuid'] for command in observation.get('commands', [])}
    terminals = {event['uuid']: event['status'] for event in events.values()
                 if event['event'] == 'terminal' and event.get('status') in (4, 5, 6)}
    if result['scenario'] in ('tracking', 'safety', 'delay'):
        assert commands and commands <= terminals.keys(), (item['label'], commands-terminals.keys())
        canceled = {event['uuid'] for event in events.values() if event['event'] == 'cancel_requested'}
        assert canceled <= terminals.keys(), (item['label'], 'unconfirmed cancellation')
        assert observation['tracking'][-1]['owner']['pending_uuid'] is None
        row['action_result_audit'] = dict(commands=len(commands),
            confirmed_command_results=len(commands & terminals.keys()),
            cancel_requests=len(canceled), confirmed_cancel_results=len(canceled & terminals.keys()),
            canceled_status5=sum(terminals[key] == 5 for key in canceled))
    if result['scenario'] in ('tracking', 'safety'):
        baseline = result['tracking_baseline']
        assert len(set(baseline['capture_ns'])) >= 3
        assert baseline['command_count'] == 0
        assert max(baseline['measurement_walls']) <= baseline['finished_monotonic']
        assert baseline['finished_monotonic'] <= result['tracking_session']['requested_monotonic']
        row['tracking_baseline'] = baseline
    rows.append(row)

for p, digest in frozen['snapshot']['files'].items():
    assert hashlib.sha256((root/'source_archive'/p).read_bytes()).hexdigest() == digest, p

legacy = []
for engine in ('mujoco', 'gazebo'):
    folder = legacy_root/('legacy_'+engine)
    wrapper = json.loads((folder/'result.json').read_text())
    result = json.loads((folder/'native/result.json').read_text())
    assert wrapper['status'] == result['status'] == 'PASS'
    assert result['runtime_shutdown'] == result['engine_shutdown'] == 'PASS'
    assert all(entry['returncode'] == 0 and not entry['forced_cleanup']
               and not entry['residual_live_pids'] for entry in result['cleanup'])
    residuals = json.loads((folder/'residual-observation.json').read_text())
    assert not residuals['live_engines_after']
    legacy.append(dict(engine=engine, run_id=wrapper['run_id'], result=result))

if supplement:
    repo = Path.cwd()
    for p, digest in supplement['snapshot']['files'].items():
        assert hashlib.sha256((repo/p).read_bytes()).hexdigest() == digest, p
        assert hashlib.sha256((legacy_root/'source_archive'/p).read_bytes()).hexdigest() == digest, p

output = dict(status='PASS', batch_uuid=frozen['batch_uuid'], native_trials=22,
    original_matrix_trials=20, additional_gazebo_reliability_trials=2,
    legacy_trials=2, rows=rows, legacy=legacy,
    legacy_root=str(legacy_root), retained_legacy_failures=retained_legacy_failures,
    probe_only_supplement=supplement,
    source_files=len(frozen['snapshot']['files']), installed_files=len(frozen['installed']),
    notes=['All 22 original native trials passed without failed trials being excluded.',
           'One failed legacy trial is retained explicitly; only its synthetic input '
           'generator changed before both-engine legacy revalidation. Runtime/installation '
           'and all sources used by the 22 native trials are unchanged.',
           'Arm owner terminal events come from the real result future, not status/cancel ACK.',
           'Read the retained earlier failures and diagnostic boundary interposition separately.',
           'PPO loaded walking, MoveIt, physical grasp, Nav2 and real hardware remain unverified.'])
with (root/'FINAL_ACCEPTANCE_SUMMARY.json').open('x') as stream:
    json.dump(output, stream, indent=2)
print(json.dumps({key: value for key, value in output.items()
                  if key not in ('rows', 'legacy', 'probe_only_supplement', 'retained_legacy_failures')}, indent=2))
