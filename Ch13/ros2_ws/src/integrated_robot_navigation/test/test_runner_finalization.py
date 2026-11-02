"""Failed cleanup must retain truthful partial evidence and remain failed."""
import json
import pytest
import run_navigation_13_5 as runner


def test_cleanup_exception_preserves_observed_fields_without_inventing_join(tmp_path):
    path=tmp_path/'teardown.json'
    with pytest.raises(RuntimeError,match='observer not joined'):
        with runner.teardown_checkpoint(path) as state:
            state.update(parent_reaped=True,engine_exit=True)
            raise RuntimeError('observer not joined')
    saved=json.loads(path.read_text())
    assert saved['parent_reaped'] is True and saved['engine_exit'] is True
    assert saved['finalization_complete'] is False
    assert saved.get('probe_receiver_joined') is not True


@pytest.mark.parametrize('engine,clock,g2,expected',[
    ('mujoco','relay100',True,'direct_single_owner'),
    ('mujoco','relay100',False,'direct_single_owner'),
    ('gazebo','relay100',True,'direct_single_owner'),
    ('gazebo','relay100',False,'direct_single_owner'),
    ('mujoco','native',True,'single_worker'),
    ('gazebo','native',False,'single_worker')])
def test_executor_metadata_matches_the_scoped_actual_factory(engine,clock,g2,expected):
    assert runner.crawl_dispatch_mode(engine,clock,g2)==expected
