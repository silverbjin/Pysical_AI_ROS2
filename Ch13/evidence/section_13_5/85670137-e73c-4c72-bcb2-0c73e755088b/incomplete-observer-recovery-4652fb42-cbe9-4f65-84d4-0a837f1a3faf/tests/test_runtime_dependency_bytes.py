"""Reused runtime/vision bytes cannot silently differ from recorded sources."""
import hashlib
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
import run_navigation_13_5 as runner


def layout(tmp_path):
    repo=tmp_path/'repo';source=repo/'own_dependency';installed=tmp_path/'install/lib/own_dependency'
    source.mkdir(parents=True);installed.mkdir(parents=True)
    for root in (source,installed):
        (root/'__init__.py').write_text('VERSION=1\n')
        (root/'helper.py').write_text('def same(): return 42\n')
    return repo,source,installed,tmp_path/'install'


def test_source_and_actual_installed_dependency_are_hashed_together(tmp_path):
    assert hasattr(runner,'audit_python_source_bytes'),'reused dependency source binding missing'
    repo,source,installed,prefix=layout(tmp_path)
    result=runner.audit_python_source_bytes(source,installed,repo,prefix)
    assert result=={str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.py')}


@pytest.mark.parametrize('bad',['changed','missing','outside','symlink'])
def test_changed_missing_or_foreign_installed_python_dependency_fails_before_engine(tmp_path,bad):
    assert hasattr(runner,'audit_python_source_bytes'),'reused dependency source binding missing'
    repo,source,installed,prefix=layout(tmp_path)
    if bad=='changed':(installed/'helper.py').write_text('def same(): return 0\n')
    elif bad=='missing':(installed/'helper.py').unlink()
    elif bad=='outside':prefix=tmp_path/'other_install'
    else:
        foreign=tmp_path/'foreign.py';foreign.write_bytes((source/'helper.py').read_bytes())
        (installed/'helper.py').unlink();(installed/'helper.py').symlink_to(foreign)
    with pytest.raises(RuntimeError):runner.audit_python_source_bytes(source,installed,repo,prefix)


def test_actual_event_backend_version_wrapper_and_extension_files_are_recorded():
    from integrated_robot_navigation import dispatch_node
    assert hasattr(dispatch_node,'event_backend_manifest'),'installed event dependency fingerprint missing'
    report=dispatch_node.event_backend_manifest()
    assert report['rclpy_version']=='7.1.12'
    for key in ('wrapper','extension'):
        assert report[key]['sha256']==hashlib.sha256(Path(report[key]['path']).read_bytes()).hexdigest()
    assert report['callbacks']=='serial' and report['parallel_callback_groups'] is False
