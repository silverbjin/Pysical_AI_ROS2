import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest


def wrapper():
    source=Path(__file__).resolve().parents[5]/'Ch13/scripts/reuse_13_7/run_mission.py'
    spec=importlib.util.spec_from_file_location('vision_rate_wrapper',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('session,expected',[(SimpleNamespace(),15),(SimpleNamespace(vision_hz=10),10),(SimpleNamespace(vision_hz=15),15)])
def test_existing_worker_forwards_supported_rate_without_changing_legacy(session,expected):
    args=wrapper().navigation_arguments(Path('/repo'),Path('/out'),session)
    assert args==['--repo-root','/repo','--evidence','/out','--case','vision','--vision-hz',str(expected)]


@pytest.mark.parametrize('value',[0,30,None,True,10.0])
def test_invalid_rate_is_rejected_before_starting_an_engine(value):
    with pytest.raises(ValueError):wrapper().navigation_arguments(Path('/repo'),Path('/out'),SimpleNamespace(vision_hz=value))
