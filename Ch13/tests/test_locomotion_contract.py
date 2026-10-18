import numpy as np
import pytest
from ch13_sim_core.contract import load_contract
from ch13_sim_core.locomotion_contract import create_policy_core,validate_manifest

def test_full_state_extra_arm_is_ignored_and_48_observation():
    c=load_contract();core=create_policy_core()
    q=c.nominal;q[12:18]=.2
    core.update_joints(c.names[::-1],q[::-1],np.zeros(20),1.)
    core.update_imu([0,0,0,1],[0,0,0],1.)
    core.update_velocity([0,0,0],1.)
    obs=core.observation(1.)
    assert obs.shape==(48,)
    np.testing.assert_array_equal(obs[12:24],[0]*12)
    with pytest.raises(ValueError):core.update_joints(c.names[1:],q[1:],np.zeros(19),2.)

@pytest.mark.parametrize('task',['goal','avoidance','integrated'])
def test_rejects_non_locomotion_manifest(task):
    with pytest.raises(ValueError):validate_manifest({'task':task,'observation_size':48,'action_size':12,'observation_schema':'locomotion-v1-48','normalization':'none'})

def test_outputs_twelve_scaled_limited_targets():
    core=create_policy_core()
    q,_=core.process_action(np.ones(12))
    np.testing.assert_allclose(q[:3],[.1,-.4,1.1])
    assert len(core.contract.joint_names)==12
