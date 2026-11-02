import numpy as np
from ch13_control.hold_controller import fixture_targets
from ch13_sim_core.contract import load_contract

def test_fixture_only_moves_arm_and_fingers_after_explicit_enable():
    q=load_contract().nominal
    np.testing.assert_array_equal(fixture_targets(q,0),q)
    out=fixture_targets(q,6)
    np.testing.assert_array_equal(out[:12],q[:12])
    assert out[13]==-.2 and list(out[18:])==[0,0]
    np.testing.assert_array_equal(q[18:],[.035,.035])
