"""Replay real accepted inputs, then corrupt one acceptance fact at a time."""
import importlib.util,json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[5]
spec=importlib.util.spec_from_file_location('acceptance_moveit_verifier',ROOT/'Ch13/scripts/reuse_13_6/verify_moveit.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)


def evidence(tmp_path):
    fixture=json.loads((Path(__file__).parent/'fixtures/moveit_acceptance_v4.json').read_text())
    for name,value in fixture['files'].items():
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value))
    return tmp_path


def test_original_actual_moveit_evidence_is_accepted(tmp_path):
    assert verifier.verify(evidence(tmp_path))['result']=='PASS'


@pytest.mark.parametrize('corruption',['missing_terminal','remaining_pid','failed_residual','false_measurement'])
def test_action_ack_or_summary_success_cannot_replace_acceptance_facts(tmp_path,corruption):
    path=evidence(tmp_path);summary_path=path/'run/navigation_summary.json'
    summary=json.loads(summary_path.read_text())
    if corruption=='missing_terminal':
        summary['engine']['manipulation']['arm_events']=[r for r in summary['engine']['manipulation']['arm_events'] if r['event']!='measured_terminal']
    elif corruption=='remaining_pid':summary['remaining_launch_pids']=[424242]
    elif corruption=='failed_residual':(path/'post_residual.json').write_text(json.dumps({'result':'FAIL'}))
    else:
        probe_path=path/'run/moveit_probe.json';probe=json.loads(probe_path.read_text())
        probe['measurements'][0]['position_error_m']=.05;probe_path.write_text(json.dumps(probe))
    summary_path.write_text(json.dumps(summary))
    with pytest.raises(AssertionError):verifier.verify(path)
