"""Read-only acceptance audit; derived output never changes a native verdict."""
import hashlib
import json
from pathlib import Path
import sys

root = (Path(sys.argv[1]).resolve() if len(sys.argv) > 1
        else Path(__file__).resolve().parent/'final')
frozen = json.loads((root/'frozen-source.json').read_text())
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

legacy = []
for engine in ('mujoco', 'gazebo'):
    folder = root/('legacy_'+engine)
    wrapper = json.loads((folder/'result.json').read_text())
    result = json.loads((folder/'native/result.json').read_text())
    assert wrapper['status'] == result['status'] == 'PASS'
    assert result['runtime_shutdown'] == result['engine_shutdown'] == 'PASS'
    assert all(entry['returncode'] == 0 and not entry['forced_cleanup']
               and not entry['residual_live_pids'] for entry in result['cleanup'])
    residuals = json.loads((folder/'residual-observation.json').read_text())
    assert not residuals['live_engines_after']
    legacy.append(dict(engine=engine, run_id=wrapper['run_id'], result=result))

output = dict(status='PASS', batch_uuid=frozen['batch_uuid'], native_trials=22,
    original_matrix_trials=20, additional_gazebo_reliability_trials=2,
    legacy_trials=2, rows=rows, legacy=legacy,
    source_files=len(frozen['snapshot']['files']), installed_files=len(frozen['installed']),
    notes=['No failed native run excluded within this frozen batch.',
           'Arm owner terminal events come from the real result future, not status/cancel ACK.',
           'Read the retained earlier failures and diagnostic boundary interposition separately.',
           'PPO loaded walking, MoveIt, physical grasp, Nav2 and real hardware remain unverified.'])
with (root/'FINAL_ACCEPTANCE_SUMMARY.json').open('x') as stream:
    json.dump(output, stream, indent=2)
print(json.dumps({key: value for key, value in output.items() if key not in ('rows', 'legacy')}, indent=2))
