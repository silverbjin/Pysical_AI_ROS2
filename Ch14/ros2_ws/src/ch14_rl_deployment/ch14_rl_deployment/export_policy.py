"""Code 14-17; verified Ch12 bundle -> actual clipped actor -> ONNX and replay parity."""
import argparse,json,hashlib,time
from pathlib import Path
import numpy as np
import torch
from torch import nn
from quadruped_rl.ppo import load_bundle
from quadruped_rl.ros_core import PolicyContract,ControllerCore
from .policy import checked,digest,manifest_ok,contract_ok,OnnxPolicy
class ActorExport(nn.Module):
    def __init__(self,policy,low,high):
        super().__init__();self.policy=policy
        self.register_buffer("low",torch.as_tensor(low,dtype=torch.float32));self.register_buffer("high",torch.as_tensor(high,dtype=torch.float32))
    def forward(self,observation):
        return torch.clamp(self.policy.get_distribution(observation).get_actions(deterministic=True),min=self.low,max=self.high)
def write(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+"\n")
def build(bundle,checkpoint,checkpoint_sha,manifest_sha,out,scope):
    import gymnasium as gym,onnx
    from stable_baselines3.common.distributions import DiagGaussianDistribution
    from .observation_adapter import FIELDS
    if Path(checkpoint).name!=checkpoint:raise ValueError("checkpoint basename required")
    checked(bundle/checkpoint,checkpoint_sha);checked(bundle/"manifest.json",manifest_sha)
    manifest=json.loads((bundle/"manifest.json").read_text());manifest_ok(manifest)
    torch.set_num_threads(1)
    model,env,m=load_bundle(bundle,model_name=checkpoint,expected_task="locomotion",device="cpu")
    try:
        if not isinstance(model.observation_space,gym.spaces.Box) or not isinstance(model.action_space,gym.spaces.Box) or model.policy.squash_output or not isinstance(model.policy.action_dist,DiagGaussianDistribution):raise ValueError("unsupported policy distribution")
        if model.observation_space.shape!=(48,) or model.action_space.shape!=(12,) or model.observation_space.dtype!=np.float32:raise ValueError("unsupported space")
        pc=PolicyContract.from_env(env);base=env.unwrapped
        c=dict(manifest=m,policy_scope=scope,checkpoint_sha256=checkpoint_sha,manifest_sha256=manifest_sha,env_config_sha256=hashlib.sha256(json.dumps(m["env_kwargs"],sort_keys=True,separators=(",",":")).encode()).hexdigest(),
               joint_names=list(pc.joint_names),nominal=pc.nominal.tolist(),joint_limits=pc.joint_limits.tolist(),action_scale=pc.action_scale.tolist(),action_low=model.action_space.low.tolist(),action_high=model.action_space.high.tolist(),
               control_period_s=pc.dt,max_target_delta_rad=.1,startup_velocity_rad_s=1.,sensor_timeout_s=.25,max_skew_s=.1,command_timeout_s=.5,wall_watchdog_s=.5,inference_budget_s=.02,observation_fields=FIELDS,
               onnx_io=dict(input="observation",output="joint_action",input_shape=[1,48],output_shape=[1,12],dtype="float32",opset=13))
        out.mkdir(parents=True,exist_ok=False);path=out/"quadruped_policy.onnx";actor=ActorExport(model.policy,model.action_space.low,model.action_space.high).eval()
        torch.onnx.export(actor,torch.zeros(1,48,dtype=torch.float32),str(path),input_names=["observation"],output_names=["joint_action"],opset_version=13,dynamo=False)
        graph=onnx.load(str(path));onnx.checker.check_model(graph)
        assert any(o.domain in ("","ai.onnx") and o.version==13 for o in graph.opset_import)
        c["onnx_sha256"]=digest(path);contract_ok(c);cp=out/"policy_contract.json";write(cp,c);pol=OnnxPolicy(path,cp,digest(cp))
        obs,_=env.reset(seed=14);samples=[];records=[];resets=0
        for i in range(128):
            core=ControllerCore(pc)
            q=base.data.qpos[3:7].copy();xyzw=q[[1,2,3,0]]
            linear=base.get_base_linear_velocity();angular=base.get_base_angular_velocity();positions=base.data.qpos[base._qpos_ids].copy();velocities=base.data.qvel[base._qvel_ids].copy();command=base.command;last=base.last_action
            core.update_imu(xyzw,angular,1.);core.update_velocity(linear,1.,"body");core.update_joints(pc.joint_names,positions,velocities,1.);core.update_command(command,1.);core.last_action=last.copy()
            reconstructed=core.observation(1.)
            # A falling state beyond tilt limits is not a valid controller input. Reset before capture if needed.
            np.testing.assert_allclose(reconstructed,obs,atol=1e-5,rtol=1e-4)
            samples.append(obs.copy());records.append(dict(xyzw=xyzw.tolist(),angular=angular.tolist(),linear=linear.tolist(),positions=positions.tolist(),velocities=velocities.tolist(),command=command.tolist(),last_action=last.tolist(),observation=obs.tolist(),height=float(base.data.qpos[2]),sim_time=float(base.data.time)))
            action,_=model.predict(obs,deterministic=True);obs,_,done,cut,_=env.step(action)
            if done or cut:obs,_=env.reset();resets+=1
        # actual replay and separately marked numeric edge inputs, not fake sensor observations
        edge=np.stack([np.zeros(48,np.float32),np.ones(48,np.float32),-np.ones(48,np.float32),np.full(48,100,np.float32),np.full(48,-100,np.float32),np.linspace(-3,3,48,dtype=np.float32),np.linspace(3,-3,48,dtype=np.float32),np.finfo(np.float32).eps*np.ones(48,np.float32)])
        x=np.concatenate([np.stack(samples),edge]);refs=[];outputs=[];raws=[];timings=[]
        for row in x:
            ref,_=model.predict(row,deterministic=True)
            with torch.no_grad():raw=model.policy.get_distribution(torch.from_numpy(row[None])).get_actions(deterministic=True).cpu().numpy()[0]
            t=time.monotonic_ns();y,_=pol.predict(row);timings.append((time.monotonic_ns()-t)/1e6)
            np.testing.assert_allclose(y,ref,atol=1e-5,rtol=1e-4);refs.append(ref);outputs.append(y);raws.append(raw)
        ref=np.array(refs);y=np.array(outputs);raw=np.array(raws);err=np.abs(ref-y)
        np.savez_compressed(out/"parity_samples.npz",observation=x,ppo=ref,onnx=y,unclipped=raw)
        write(out/"sensor_replay.json",records)
        write(out/"parity.json",dict(status="POLICY_EXPORT_PASS",policy_scope=scope,actual_recorded_observations=128,numeric_edges=8,compared_elements=int(err.size),max_abs=float(err.max()),mean_abs=float(err.mean()),atol=1e-5,rtol=1e-4,clipped_elements=int(np.count_nonzero(np.abs(raw)>1)),episode_resets=resets,model_sha256=c["onnx_sha256"],contract_sha256=digest(cp),provider=pol.session.get_providers(),inference_ms=dict(mean=float(np.mean(timings)),p95=float(np.percentile(timings,95)),max=float(max(timings))),samples_sha256=digest(out/"parity_samples.npz"),sensor_replay_sha256=digest(out/"sensor_replay.json")))
    finally:env.close()
def main():
    p=argparse.ArgumentParser();p.add_argument("--bundle",type=Path,required=True);p.add_argument("--checkpoint",default="final_model.zip");p.add_argument("--checkpoint-sha256",required=True);p.add_argument("--manifest-sha256",required=True);p.add_argument("--out",type=Path,required=True);p.add_argument("--scope",choices=["SMOKE_ONLY","OWNER_VERIFIED_BUNDLE"],required=True);a=p.parse_args()
    build(a.bundle,a.checkpoint,a.checkpoint_sha256,a.manifest_sha256,a.out,a.scope)
if __name__=="__main__":main()
