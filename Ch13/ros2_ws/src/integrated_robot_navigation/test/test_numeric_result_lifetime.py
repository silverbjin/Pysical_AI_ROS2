"""Consumed late replies must remain accounted for, without becoming usable."""
import select,json
from types import SimpleNamespace
import pytest
from test_spatial_load_transition import inputs
from integrated_robot_navigation import load_process as module


@pytest.mark.parametrize('numeric_failure',[False,True])
def test_late_consumed_result_can_close_normally_but_never_pass_jobs(nav_robot_model,monkeypatch,numeric_failure):
    model,args=inputs(nav_robot_model);worker=module.SpatialLoadProcess(model);worker.prepare()
    if numeric_failure:args['forces_world']={f:[0.,0.,100000.] for f in model.feet}
    worker.submit(args,dict(generation=1));issued=worker._pending['submitted_wall_ns']
    try:
        assert select.select([worker._channel],[],[],1.)[0], 'actual child did not reply'
        # Reproduce the exact edge: entry is in time, then a complete response
        # is read but the post-receive deadline check finds it late.
        with monkeypatch.context() as patch:
            patch.setattr(module,'time',SimpleNamespace(monotonic_ns=lambda:issued+module.DISPATCH_NS+1))
            with pytest.raises(ValueError,match='dispatch deadline'):
                worker.poll(now_wall_ns=issued+1)
        assert worker.last_model is None
        assert worker.snapshot()['completed']==0
        assert worker.snapshot()['pending'] is False, 'reply was consumed but job lifetime was left pending'
        assert worker.snapshot()['discarded']==1
        assert worker.snapshot()['failed']==int(numeric_failure)
        assert worker.last_attempt is not None
        assert worker.last_input_id==worker.snapshot()['last_reply']['id']==1
        expected=json.loads(json.dumps(args,allow_nan=False,default=lambda value:value.tolist()))
        assert worker.last_input==expected and worker.last_context==dict(generation=1)
        with pytest.raises(ValueError,match='latched'):worker.submit(args,{})
    finally:closed=worker.close()
    assert closed['acknowledged'] and closed['parent_reaped'] and not closed['pending']
    assert closed['returncode']==0 and not closed['forced_cleanup']
    assert not module.assess_numeric_jobs(closed), 'clean close hid the deadline fault'
