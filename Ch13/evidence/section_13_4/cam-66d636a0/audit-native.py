"""Integrity gate for completed measurements; PASS is NOT native acceptance."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd()/'Ch13/scripts'))
from verify_vision_13_4 import file_digest, verdict
from run_vision_13_4 import required_checks

root = Path('Ch13/evidence/section_13_4/cam-66d636a0').resolve()
checked = 0
rows = []
for directory, expected in ((root, 23), (root/'clean', 7)):
    matrix = json.loads((directory/'matrix.json').read_text())
    assert matrix['status'] == 'FAIL' and not matrix['remaining_native_processes']
    assert matrix['source_head'] == '6828b82fd13c97dba3fc935325a741e583a830aa'
    assert len(matrix['cases']) == expected
    for alias, row in matrix['cases'].items():
        assert row['status'] in ('PASS', 'FAIL')
        assert not row['remaining_native_processes']
        value = json.loads((directory/alias/'result.json').read_text())
        wrapper = json.loads((directory/(alias+'w')/'result.json').read_text())
        assert wrapper['batch_run_id'] == matrix['batch_run_id'] and wrapper['group'] == alias
        if row['scenario'] == 'legacy':
            accepted = value.get('status') == 'PASS' and value.get('runtime_shutdown') == 'PASS'
            accepted = accepted and wrapper.get('returncode') == 0
            for log in (directory/alias).glob('*.log'):
                accepted = accepted and not any(marker in log.read_text() for marker in (
                    'Traceback', 'escalating to', 'process has died', 'failed to terminate'))
        else:
            accepted = verdict(value, required_checks(row['scenario'], engine=row['engine'],
                camera_backend=row['backend'])) == 'PASS'
            assert value['started_at'] >= wrapper['started_at']
            assert value['run_id'] == row['run_id']
            assert value['cleanup'] and all(not item['residual_live_pids'] for item in value['cleanup'])
        assert row['status'] == ('PASS' if accepted else 'FAIL')
        for result in (value, wrapper):
            for item in result.get('artifacts', []):
                path = (Path(result['artifact_root'])/item['path']).resolve(strict=True)
                assert path.is_relative_to(Path(result['artifact_root']).resolve())
                assert path.stat().st_size == item['size'] and file_digest(path) == item['sha256']
                checked += 1
        rows.append(dict(cohort=directory.name, case=alias, status=row['status'],
                         scenario=row['scenario'], engine=row['engine']))
report = dict(integrity='PASS', native_acceptance='FAIL', measured_trials=len(rows),
              artifacts_verified=checked, source_head=matrix['source_head'],
              note='Integrity only: failed native trials remain FAIL; no new engine executed.', cases=rows)
print(json.dumps(report, indent=2))
