import json
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

import argparse
parser = argparse.ArgumentParser(description='Ubuntu/WSLg real viewer shutdown regression')
parser.add_argument('--output',type=Path,required=True)
root = parser.parse_args().output
root.mkdir(parents=True,exist_ok=True)
(root/'viewer_shutdown_repeat.json').unlink(missing_ok=True)
runs = []
for section in ('12.1','12.2','12.3','12.5','12.6'):
    for interrupt in (False,True,True):
        code = '''import sys
from quadruped_rl import QuadrupedEnv,QuadrupedTrainingEnv,QuadrupedLocomotionEnv,QuadrupedGoalEnv,QuadrupedAvoidanceEnv
from quadruped_rl.demo import stand_action
import time
classes = {'12.1':QuadrupedEnv,'12.2':QuadrupedTrainingEnv,'12.3':QuadrupedLocomotionEnv,'12.5':QuadrupedGoalEnv,'12.6':QuadrupedAvoidanceEnv}
env = classes[sys.argv[1]](render_mode='human')
try:
    env.reset(seed=42)
    print('VIEWER_READY',flush=True)
    for _ in range(100000 if sys.argv[2]=='True' else 20):
        _,_,done,cut,_ = env.step(stand_action(env))
        if done or cut: env.reset()
        time.sleep(env.dt)
except KeyboardInterrupt:
    sys.exit(130)
finally:
    env.close()
'''
        child = subprocess.Popen([sys.executable,'-u','-c',code,section,str(interrupt)],
            cwd='/tmp',stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            assert select.select([child.stdout],[],[],30)[0]
            assert child.stdout.readline().strip() == 'VIEWER_READY'
            if interrupt:
                time.sleep(.2)
                child.send_signal(signal.SIGINT)
            out,err = child.communicate(timeout=20)
            expected = 130 if interrupt else 0
            assert child.returncode == expected and 'Traceback' not in err,(section,child.returncode,err)
            runs.append(dict(section=section,sigint=interrupt,exit=child.returncode,stderr=err))
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
report = dict(status='PASS',runs=runs,normal_exits=5,sigint_exits=10)
(root/'viewer_shutdown_repeat.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(status='PASS',normal_exits=5,sigint_exits=10)))
