import copy,json,os
from pathlib import Path
import numpy as np,pytest
from ch14_rl_deployment.policy import OnnxPolicy,manifest_ok,digest,contract_ok
from ch14_rl_deployment.observation_adapter import pack_observation
@pytest.fixture
def paths():
    root=Path(os.environ["G07_EXPORT"]);return root/"quadruped_policy.onnx",root/"policy_contract.json"
@pytest.fixture
def policy(paths):return OnnxPolicy(*paths,digest(paths[1]))
@pytest.mark.parametrize("key,value",[("task","goal"),("observation_schema","goal-polar-sincos-v1-48"),("normalization","VecNormalize"),("observation_size",41),("action_size",6)])
def test_manifest(paths,key,value):
    m=json.loads(paths[1].read_text())["manifest"];m[key]=value
    with pytest.raises(ValueError):manifest_ok(m)
@pytest.mark.parametrize("x",[np.zeros(41,np.float32),np.full(48,np.nan,np.float32),np.full(48,np.inf,np.float32),np.zeros(48,np.float64),np.zeros((2,48),np.float32)])
def test_input(policy,x):
    with pytest.raises(ValueError):policy.predict(x)
def test_api(policy):
    x=np.zeros(48,np.float32)
    assert policy.predict(x)[0].shape==(12,)
    assert policy.predict(x[None])[0].shape==(1,12)
    with pytest.raises(ValueError):policy.predict(x,deterministic=False)
    with pytest.raises(ValueError):policy.predict(x,state=np.zeros(1))
def test_hash(paths,tmp_path):
    with pytest.raises(ValueError):OnnxPolicy(*paths,"0"*64)
    bad=tmp_path/"bad.onnx";bad.write_bytes(b"bad")
    with pytest.raises(ValueError):OnnxPolicy(bad,paths[1],digest(paths[1]))
def test_contract(paths):
    c=json.loads(paths[1].read_text());c["action_scale"]=[.5]*12
    with pytest.raises(ValueError):contract_ok(c)
def test_pack():
    assert pack_observation(*[np.zeros(n) for n in [3,3,3,3,12,12,12]]).shape==(48,)
    with pytest.raises(ValueError):pack_observation(*[np.zeros(n) for n in [3,3,3,3,12,12,5]])
