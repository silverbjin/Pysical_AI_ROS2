import numpy as np
import pytest
from sensor_msgs.msg import JointState
from ch13_sim_core.contract import load_contract
from ch13_control.state_monitor import StateValidator

def state():
    c=load_contract();msg=JointState();msg.name=list(c.names[::-1]);msg.position=c.nominal[::-1].tolist();msg.header.stamp.sec=1
    return msg

def test_orders_twenty_and_preserves_stamp():
    out=StateValidator().validate(state())
    assert out.header.stamp.sec==1
    assert out.name[0]=='fr_hip_joint'
    np.testing.assert_allclose(out.position[:3],[0,-.5,1])

@pytest.mark.parametrize('kind',['duplicate','missing','nan','time'])
def test_rejects_invalid_state(kind):
    v=StateValidator();m=state()
    if kind=='duplicate':m.name[0]=m.name[1]
    if kind=='missing':m.name.pop();m.position.pop()
    if kind=='nan':m.position[0]=float('nan')
    if kind=='time':v.validate(m)
    with pytest.raises(ValueError):v.validate(m)
