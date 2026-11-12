import importlib
import json

import pytest


def test_reader_preserves_historical_failure_even_when_bt_finished(tmp_path):
    (tmp_path/'trial.json').write_text(json.dumps(dict(success=False,scenario='level2_obstacles',sim_s=260.)))
    (tmp_path/'bt_summary.json').write_text(json.dumps(dict(terminal='SUCCESS',port=dict(completed={k:{} for k in ('pick','return','place','finish')}))))
    original={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    data=importlib.import_module('ch13_system_validation.case_reader').read_case(tmp_path)
    assert data['result']=='FAIL' and data['bt_terminal']=='SUCCESS'
    assert data['scope']=='historical_full_mission'
    assert 'place' in data['completed']
    assert original=={p.name:p.read_bytes() for p in tmp_path.iterdir()}


def test_reader_distinguishes_basic_pass_from_full_mission(tmp_path):
    (tmp_path/'basic_result.json').write_text(json.dumps(dict(result='PASS',success=True,
        scope='basic_navigation_observation_only',full_mission_success=False)))
    data=importlib.import_module('ch13_system_validation.case_reader').read_case(tmp_path)
    assert data['result']=='PASS' and data['full_mission_success'] is False


def test_reader_refuses_folder_without_result(tmp_path):
    with pytest.raises(ValueError):
        importlib.import_module('ch13_system_validation.case_reader').read_case(tmp_path)
