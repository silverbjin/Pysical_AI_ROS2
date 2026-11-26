"""Static FP32 ONNX CPU actor; no implicit provider or stochastic fallback."""
import hashlib,json,re
from pathlib import Path
import numpy as np
def digest(path):
    p=Path(path)
    if not p.is_file() or p.is_symlink():raise ValueError("regular file required")
    return hashlib.sha256(p.read_bytes()).hexdigest()
def checked(path,expected):
    if not re.fullmatch("[0-9a-f]{64}",expected or "") or digest(path)!=expected:raise ValueError("SHA256 mismatch")
def manifest_ok(m):
    if (m.get("format_version"),m.get("task"),m.get("observation_schema"),m.get("normalization"),m.get("observation_size"),m.get("action_size"))!=(1,"locomotion","locomotion-v1-48","none",48,12):raise ValueError("unsupported task/schema/normalization/shape")
    if not isinstance(m.get("env_kwargs"),dict):raise ValueError("missing environment config")
def contract_ok(c):
    manifest_ok(c["manifest"])
    if c["policy_scope"] not in ("SMOKE_ONLY","OWNER_VERIFIED_BUNDLE"):raise ValueError("policy scope")
    names=c["joint_names"];n=np.asarray(c["nominal"]);scale=np.asarray(c["action_scale"]);limits=np.asarray(c["joint_limits"])
    if len(names)!=12 or len(set(names))!=12 or not all(isinstance(x,str) and x for x in names):raise ValueError("joint names")
    if n.shape!=(12,) or not np.array_equal(n,np.tile([0.,-.5,1.],4)) or scale.shape!=(12,) or not np.allclose(scale,.35) or limits.shape!=(12,2) or not np.isfinite(limits).all() or np.any(limits[:,0]>=limits[:,1]) or np.any(n<limits[:,0]) or np.any(n>limits[:,1]):raise ValueError("position contract")
    if not np.isclose(c["control_period_s"],.02) or c["max_target_delta_rad"]!=.1 or c["sensor_timeout_s"]!=.25 or c["max_skew_s"]!=.1 or c["command_timeout_s"]!=.5 or c["wall_watchdog_s"]!=.5 or c["inference_budget_s"]!=.02:raise ValueError("time/limit contract")
    if c["action_low"]!=[-1.]*12 or c["action_high"]!=[1.]*12:raise ValueError("action space")
    if c["onnx_io"]!={"input":"observation","output":"joint_action","input_shape":[1,48],"output_shape":[1,12],"dtype":"float32","opset":13}:raise ValueError("ONNX contract")
    for k in ("checkpoint_sha256","manifest_sha256","env_config_sha256","onnx_sha256"):
        if not re.fullmatch("[0-9a-f]{64}",c[k]):raise ValueError("missing digest "+k)
    return c
class OnnxPolicy:
    def __init__(self,model,contract,expected_contract_sha):
        checked(contract,expected_contract_sha)
        self.contract=contract_ok(json.loads(Path(contract).read_text()))
        checked(model,self.contract["onnx_sha256"])
        import onnxruntime as ort
        o=ort.SessionOptions();o.intra_op_num_threads=1;o.inter_op_num_threads=1
        self.session=ort.InferenceSession(str(model),sess_options=o,providers=["CPUExecutionProvider"]);self.session.disable_fallback()
        ins,outs=self.session.get_inputs(),self.session.get_outputs()
        if self.session.get_providers()!=["CPUExecutionProvider"] or len(ins)!=1 or len(outs)!=1 or (ins[0].name,ins[0].shape,ins[0].type,outs[0].name,outs[0].shape,outs[0].type)!=("observation",[1,48],"tensor(float)","joint_action",[1,12],"tensor(float)"):raise ValueError("ONNX IO/provider")
    def predict(self,observation,state=None,episode_start=None,deterministic=True):
        if state is not None or episode_start is not None or deterministic is not True:raise ValueError("only deterministic stateless actor")
        x=np.asarray(observation)
        if x.dtype!=np.float32 or x.shape not in ((48,),(1,48)) or not np.isfinite(x).all():raise ValueError("48 finite FP32 observations required")
        y=self.session.run(["joint_action"],{"observation":x.reshape(1,48)})[0]
        if y.shape!=(1,12) or y.dtype!=np.float32 or not np.isfinite(y).all() or np.any(np.abs(y)>1):raise ValueError("invalid action")
        return (y[0] if x.ndim==1 else y),None
