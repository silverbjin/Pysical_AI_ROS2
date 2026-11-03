import pytest
from ch13_manipulation_reuse.planning_contract import execution_admission,cartesian_complete


def test_partial_cartesian_never_executes_and_errors_rejected():
    assert cartesian_complete(1.,1,.002)
    for fraction,error,residual in [(.91,1,.002),(1.,-1,.002),(1.,1,.02),(float('nan'),1,.002)]:
        assert not cartesian_complete(fraction,error,residual)


def test_stale_scene_capture_or_start_state_rejected():
    assert execution_admission(7,7,[0.]*6,[.001]*6,1_000_000_000,1_100_000_000,10.,10.1)
    assert not execution_admission(7,8,[0.]*6,[.001]*6,1_000_000_000,1_100_000_000,10.,10.1)
    assert not execution_admission(7,7,[0.]*6,[.1]*6,1_000_000_000,1_100_000_000,10.,10.1)
    assert not execution_admission(7,7,[0.]*6,[.001]*6,1_000_000_000,1_400_000_000,10.,10.1)
    assert not execution_admission(7,7,[0.]*6,[.001]*6,1_000_000_000,1_100_000_000,10.,10.4)
