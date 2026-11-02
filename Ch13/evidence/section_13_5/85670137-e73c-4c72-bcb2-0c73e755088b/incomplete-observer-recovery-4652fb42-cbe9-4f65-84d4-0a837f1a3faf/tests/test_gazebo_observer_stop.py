"""Transport ACK proves native observer egress stopped, NOT engine exit."""
import subprocess
from types import SimpleNamespace
import pytest


@pytest.mark.parametrize('code,stdout,expected',[(0,'data: true\n',True),
    (0,'data: false\n',False),(1,'data: true\n',False),(0,'',False),
    (0,'not_data: true\n',False)])
def test_native_observer_stop_requires_exact_success_reply(monkeypatch,code,stdout,expected):
    import run_navigation_13_5 as runner
    calls = []
    def cli(command,**kwargs):
        calls.append((command,kwargs))
        return SimpleNamespace(returncode=code,stdout=stdout,stderr='')
    monkeypatch.setattr(runner.subprocess,'run',cli)
    result = runner.stop_gazebo_observer()
    assert result['confirmed'] is expected
    assert calls == [(['gz','service','-s','/navigation/stop_native_observer',
        '--reqtype','gz.msgs.Empty','--reptype','gz.msgs.Boolean','--timeout','2000','--req',''],
        dict(capture_output=True,text=True,timeout=5.))]


def test_observer_stop_timeout_is_failed_evidence_not_engine_success(monkeypatch):
    import run_navigation_13_5 as runner
    def cli(*args,**kwargs):
        raise subprocess.TimeoutExpired(args[0],5.)
    monkeypatch.setattr(runner.subprocess,'run',cli)
    result = runner.stop_gazebo_observer()
    assert result['confirmed'] is False and result['error']
