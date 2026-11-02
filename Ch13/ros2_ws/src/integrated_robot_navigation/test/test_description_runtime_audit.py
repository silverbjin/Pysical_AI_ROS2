"""Catch executing a stale installed launch after changing native PID ownership."""
import hashlib
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]/'scripts'))
import run_navigation_13_5 as runner


@pytest.mark.parametrize('fault', ['', 'changed', 'missing', 'source_symlink'])
def test_description_launch_source_install_bytes_are_bound(tmp_path, fault):
    repo, share = tmp_path/'repo', tmp_path/'install/share/integrated_robot_description'
    source = repo/'Ch13/ros2_ws/src/integrated_robot_description/launch'
    source.mkdir(parents=True)
    (share/'launch').mkdir(parents=True)
    for engine in ('mujoco', 'gazebo'):
        content = ('# '+engine+' fixture\n').encode()
        (source/(engine+'.launch.py')).write_bytes(content)
        (share/'launch'/(engine+'.launch.py')).write_bytes(content)
    target = share/'launch/gazebo.launch.py'
    if fault == 'changed':
        target.write_text('# stale launch\n')
    elif fault == 'missing':
        target.unlink()
    elif fault == 'source_symlink':
        target.unlink()
        target.symlink_to(source/'gazebo.launch.py')
    assert hasattr(runner, 'audit_description_launches'), 'description launch byte audit missing'
    if fault:
        with pytest.raises(RuntimeError, match='description launch'):
            runner.audit_description_launches(repo, share)
    else:
        actual = runner.audit_description_launches(repo, share)
        expected = {'Ch13/ros2_ws/src/integrated_robot_description/launch/'+engine+'.launch.py':
            hashlib.sha256(('# '+engine+' fixture\n').encode()).hexdigest()
            for engine in ('mujoco', 'gazebo')}
        assert actual == expected
