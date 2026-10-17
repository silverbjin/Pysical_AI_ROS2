import json
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

from quadruped_rl.ppo import load_bundle

import argparse
parser = argparse.ArgumentParser(description='Real SIGINT during PPO learning and checkpoint reload')
parser.add_argument('--output',type=Path,required=True)
destination = parser.parse_args().output
destination.mkdir(parents=True,exist_ok=True)
(destination/'interrupt.json').unlink(missing_ok=True)
root = destination/'run'
code = '''import sys
from stable_baselines3 import PPO
from quadruped_rl.ppo import train
original = PPO.learn
def marked_learn(self,*args,**kwargs):
    print("TRAINING_READY",flush=True)
    return original(self,*args,**kwargs)
PPO.learn = marked_learn
try:
    train(sys.argv[1],total_timesteps=1000000,n_envs=1,n_steps=64,batch_size=64,
          n_epochs=2,eval_episodes=1,eval_every=10000,max_episode_steps=100)
except KeyboardInterrupt:
    sys.exit(130)
'''
child = subprocess.Popen([sys.executable,'-u','-c',code,str(root)],
    stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
    assert select.select([child.stdout],[],[],40)[0]
    assert child.stdout.readline().strip() == 'TRAINING_READY'
    time.sleep(1)
    child.send_signal(signal.SIGINT)
    out,err = child.communicate(timeout=30)
    assert child.returncode == 130 and 'Traceback' not in err,(child.returncode,err)
    assert json.loads((root/'result.json').read_text())['status'] == 'INTERRUPTED'
    model,env,_ = load_bundle(root,model_name='interrupted_model.zip')
    try:
        obs,_ = env.reset(seed=42)
        action,_ = model.predict(obs,deterministic=True)
        env.step(action)
    finally:
        env.close()
finally:
    if child.poll() is None:
        child.kill()
        child.wait()
report = dict(status='PASS',exit_code=child.returncode,interrupted_model_reload=True)
(destination/'interrupt.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
