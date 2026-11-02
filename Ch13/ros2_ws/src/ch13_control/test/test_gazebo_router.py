import numpy as np
import pytest
from ch13_control.gazebo_router import route_targets
from ch13_sim_core.contract import load_contract

def test_maps_permuted_named_commands_and_rejects_unknown():
    c=load_contract();values=np.arange(20,dtype=float)*.001
    result=route_targets(c.names[::-1],values[::-1],c)
    assert result['arm_joint_1']==.012
    assert result['fr_hip_joint']==0
    with pytest.raises(ValueError):route_targets(c.names+('unknown',),list(values)+[0],c)
    with pytest.raises(ValueError):route_targets(c.names[:-1],values[:-1],c)
