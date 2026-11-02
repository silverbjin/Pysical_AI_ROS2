"""Unprivileged foreground lifetime; never changes services or clocks."""
import importlib,importlib.util,os,sys
import pytest

def api():
    assert importlib.util.find_spec('distro_session'), 'owned foreground distro lifetime missing'
    return importlib.import_module('distro_session')

def test_foreground_session_proves_own_uid_pid_and_init_and_closes_without_signal(tmp_path):
    module=api()
    owner=module.DistroSession([sys.executable],label='local_fixture',directory=tmp_path)
    try:
        value=owner.inspect()
        assert value['active'] in ('active','inactive') and value['init_start_ticks']>0
        assert owner.identity['uid']==os.getuid() and owner.identity['pid']!=os.getpid()
        assert value['boot']==owner.identity['boot']
        owner.check()
    finally:owner.close()
    report=owner.report()
    assert report['joined'] and report['returncode']==0 and report['close_acknowledged']
    with pytest.raises(RuntimeError):owner.inspect()

def test_parent_eof_is_failed_and_does_not_restart_or_signal_a_replacement(tmp_path):
    owner=api().DistroSession([sys.executable],label='eof_fixture',directory=tmp_path)
    pid=owner.identity['pid'];owner.process.stdin.close()
    try:
        owner.process.wait(timeout=5.)
        with pytest.raises(RuntimeError):owner.check()
        with pytest.raises(RuntimeError):owner.close()
        assert owner.identity['pid']==pid and owner.report()['returncode']!=0
    finally:
        owner.process.wait(timeout=5.);owner.process.stdout.close();owner.stderr.close()

@pytest.mark.parametrize('field',['boot','init_start_ticks','machine_sha256'])
def test_privileged_service_boundary_rejects_replacement_before_any_operation(field):
    module=api();assert hasattr(module,'guarded_service'), 'service action identity guard missing'
    current=dict(uid=0,boot='boot',init_start_ticks=10,machine_sha256='a'*64)
    expected={key:current[key] for key in ('boot','init_start_ticks','machine_sha256')}
    expected[field]='different' if field!='init_start_ticks' else 20
    calls=[]
    with pytest.raises(RuntimeError):module.guarded_service('stop',expected,current,calls.append)
    assert not calls

def test_privileged_boundary_only_operates_the_approved_named_service():
    module=api();assert hasattr(module,'guarded_service'), 'service action identity guard missing'
    current=dict(uid=0,boot='boot',init_start_ticks=10,machine_sha256='a'*64)
    expected={key:current[key] for key in ('boot','init_start_ticks','machine_sha256')}
    calls=[];module.guarded_service('stop',expected,current,calls.append)
    assert calls==[['systemctl','stop','systemd-timesyncd.service']]
    with pytest.raises(RuntimeError):module.guarded_service('restart',expected,current,calls.append)
    assert len(calls)==1
