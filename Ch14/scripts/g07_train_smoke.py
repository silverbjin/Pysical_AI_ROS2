"""One actual Ch12 §12.8 smoke training; not a trained-walking claim."""
import argparse,json,hashlib
from pathlib import Path
from quadruped_rl.ppo import train
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    root=a.out/"smoke_bundle"
    # Exact historical training configuration, single call, never retry internally.
    result=train(root,task="locomotion",total_timesteps=2048,n_envs=2,backend="dummy",device="cpu",seed=42,n_steps=128,batch_size=64,n_epochs=2,learning_rate=.0003,gamma=.99,ent_coef=.005,eval_every=512,eval_episodes=2,checkpoint_every=512,max_episode_steps=200)
    assert result["status"]=="PASS" and result["timesteps"]==2048 and result["parameter_delta"]>0
    receipt=dict(status="SMOKE_ONLY",provenance="new local training with copied Ch12 source; no original checkpoint recovered",training_calls=1,actual_transitions=result["timesteps"],checkpoint="final_model.zip",checkpoint_sha256=sha(root/"final_model.zip"),manifest_sha256=sha(root/"manifest.json"),training_result=result)
    (a.out/"smoke-receipt.json").write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
if __name__=="__main__":main()
