"""Configuration witnesses are separate from real contact/task acceptance."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
import run_navigation_13_5 as runner


def records(tmp_path):
    library=tmp_path/'libdart.so.6.13.2';library.write_bytes(b'explicit metadata test library fixture')
    probe=dict(current_m=0.,header_version='6.13.2',library_path=str(library),
        library_sha256=hashlib.sha256(library.read_bytes()).hexdigest())
    state=dict(schema=1,mode='allowance50um',requested_m=.00005,before_m=0.,effective_m=.00005,
        world_count=1,explicit_g1=True,header_version='6.13.2',library_path=str(library))
    rows=[dict(capture_ns=i*20_000_000,sequence=i,epoch=0,stage=stage,
        dart_contact_configuration=deepcopy(state)) for i,stage in enumerate(('stand','calibrate'),1)]
    return rows,probe


def test_dart_setting_requires_actual_native_witnesses_in_both_operational_phases(tmp_path):
    assert hasattr(runner,'assess_dart_contact_configuration'),'native DART configuration assessor missing'
    rows,probe=records(tmp_path)
    result=runner.assess_dart_contact_configuration(rows,probe)
    assert result['passed'] and result['records']==2
    assert result['scope']=='native_api_configuration_not_contact_task_success'


@pytest.mark.parametrize('fault',['empty','missing','effective','before','worlds','flag','version',
    'provider','changed_library','probe_already_changed','duplicate','missing_calibration'])
def test_dart_setting_rejects_unapplied_misbound_or_later_changed_values(tmp_path,fault):
    assert hasattr(runner,'assess_dart_contact_configuration'),'native DART configuration assessor missing'
    rows,probe=records(tmp_path)
    state=rows[-1]['dart_contact_configuration']
    if fault=='empty':rows=[]
    elif fault=='missing':rows[-1].pop('dart_contact_configuration')
    elif fault=='effective':state['effective_m']=0.
    elif fault=='before':state['before_m']=.00005
    elif fault=='worlds':state['world_count']=2
    elif fault=='flag':state['explicit_g1']=False
    elif fault=='version':state['header_version']='6.19.0'
    elif fault=='provider':state['library_path']='/unrelated/libdart.so.6.13.2'
    elif fault=='changed_library':Path(probe['library_path']).write_bytes(b'changed fixture bytes')
    elif fault=='probe_already_changed':probe['current_m']=.00005
    elif fault=='duplicate':rows.append(deepcopy(rows[-1]))
    elif fault=='missing_calibration':rows.pop()
    assert not runner.assess_dart_contact_configuration(rows,probe)['passed']


def test_dart_required_check_is_additive_and_not_available_for_mujoco():
    assert hasattr(runner,'native_required_checks'),'explicit experiment requirements binding missing'
    baseline=runner.native_required_checks('native','native','gazebo')
    assert len(baseline)==23
    experiment=runner.native_required_checks('relay100','allowance50um','gazebo')
    assert experiment-baseline=={'control_clock_contract','dart_contact_contract'}
    assert baseline<=experiment and len(experiment)==25
    with pytest.raises(ValueError):runner.native_required_checks('native','allowance50um','mujoco')
