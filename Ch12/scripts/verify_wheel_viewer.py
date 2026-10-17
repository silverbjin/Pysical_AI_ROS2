import importlib.metadata
import json
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

import numpy as np
import quadruped_rl
from quadruped_rl.ppo import load_bundle

import argparse
parser = argparse.ArgumentParser(description='Real wheel viewer, saved policy and SIGINT regression')
parser.add_argument('--bundle',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--wheel-root',type=Path,required=True)
args = parser.parse_args()
evidence = args.output
evidence.mkdir(parents=True,exist_ok=True)
(evidence/'wheel_human.json').unlink(missing_ok=True)
assert Path(quadruped_rl.__file__).resolve().is_relative_to(args.wheel_root.resolve())
assert importlib.metadata.version('physical-ai-quadruped-rl') == '0.5.0'
model,env,manifest = load_bundle(args.bundle,render_mode='human')
try:
    obs,_ = env.reset(seed=42)
    assert env.unwrapped._viewer.is_running()
    peak_trail = 0
    for _ in range(100):
        action,_ = model.predict(obs,deterministic=True)
        obs,_,done,cut,_ = env.step(action)
        assert np.isfinite(obs).all()
        peak_trail = max(peak_trail,env.unwrapped._viewer.user_scn.ngeom)
        if done or cut:
            obs,_ = env.reset()
        time.sleep(.02)
    assert peak_trail > 1
    assert env.unwrapped._viewer.is_running()
finally:
    env.close()
assert env.unwrapped._viewer is None

code = '''import sys
from quadruped_rl.goal_demo import main
print("READY",flush=True)
sys.exit(main(["--render","--policy","stand","--steps","1000000"]))
'''
child = subprocess.Popen([sys.executable,'-u','-c',code],cwd='/tmp',
    stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
    assert select.select([child.stdout],[],[],20)[0]
    assert child.stdout.readline().strip() == 'READY'
    time.sleep(2)
    child.send_signal(signal.SIGINT)
    out,err = child.communicate(timeout=20)
    assert child.returncode == 130 and 'Traceback' not in err,(child.returncode,err)
finally:
    if child.poll() is None:
        child.kill()
        child.wait()
report = dict(status='PASS',version='0.5.0',wheel_package=quadruped_rl.__file__,
    policy_source='short PPO smoke model; navigation ability not established',
    viewer_running=True,steps=100,peak_trail_geoms=peak_trail,viewer_closed=True,
    ctrl_c_exit=child.returncode)
(evidence/'wheel_human.json').write_text(json.dumps(report,indent=2)+'\n')
(evidence/'ctrl_c.log').write_text(err)
print(json.dumps(report,indent=2))
