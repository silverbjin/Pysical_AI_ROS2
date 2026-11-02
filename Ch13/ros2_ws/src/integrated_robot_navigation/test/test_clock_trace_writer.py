"""A healthy producer/exit code cannot substitute for the writer's real join."""
from copy import deepcopy
from test_control_clock_runner import runner,good_rows
import pytest

def state():
    return dict(scope='bounded_file_worker_no_ROS_clock_or_commands',capacity=128,
        maximum_bytes=4194304,accepted=4,written=4,pending_records=0,pending_bytes=0,
        peak_records=3,peak_bytes=2048,in_flight=False,closed=True,joined=True,drained=True,error='')

def test_normal_clock_trace_requires_actual_writer_drain_and_join():
    assert hasattr(runner,'assess_control_clock_writer'),'writer close not assessed'
    assert runner.assess_control_clock_writer(state(),good_rows())['passed']

@pytest.mark.parametrize('key,value', [('joined',False),('drained',False),('closed',False),
    ('error','trace_queue_capacity'),('written',3),('accepted',5),('pending_records',1),
    ('pending_bytes',1),('in_flight',True),('capacity',0),('peak_records',129),('peak_bytes',4194305)])
def test_partial_or_failed_writer_never_counts_as_normal_close(key,value):
    assert hasattr(runner,'assess_control_clock_writer'),'writer close not assessed'
    bad=deepcopy(state());bad[key]=value
    assert not runner.assess_control_clock_writer(bad,good_rows())['passed']
