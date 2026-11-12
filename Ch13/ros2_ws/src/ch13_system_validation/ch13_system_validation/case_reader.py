"""Read preserved results without rewriting verdicts or granting live authority."""
import json
from pathlib import Path


def read_case(folder):
    folder = Path(folder)
    def load(name):
        path = folder/name
        return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    basic = (folder/'basic_result.json').is_file()
    if basic and (folder/'trial.json').exists():
        raise ValueError('mixed basic/full results in one case')
    name = 'basic_result.json' if basic else 'trial.json'
    if not (folder/name).is_file():
        raise ValueError('no basic_result.json or trial.json in case')
    row, bt, source = load(name), load('bt_summary.json'), load('source_manifest.json')
    return dict(case=folder.name, result=row.get('result', 'PASS' if row.get('success') is True else 'FAIL'),
        scope=row.get('scope', 'historical_full_mission'), scenario=row.get('scenario'),
        source_revision=source.get('revision'), bt_terminal=bt.get('terminal'),
        completed=list(bt.get('port', {}).get('completed', {})),
        full_mission_success=False if basic else row.get('success') is True,
        sim_s=row.get('sim_s'), wall_s=row.get('wall_s'),
        physical=row.get('physical'), checks=row.get('checks'),
        worker_joined=bt.get('worker_joined'),
        error=bt.get('port', {}).get('error', ''),
        note='read-only saved results; BT SUCCESS and full mission acceptance are different')
