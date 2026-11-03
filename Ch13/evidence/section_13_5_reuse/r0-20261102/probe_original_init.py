import os,sys,json,time,builtins,traceback
from pathlib import Path
root=Path(__file__).resolve().parents[4]
up=root.parent/'upstream-iit-locomanipulation-d010212'
sys.path.insert(0,str(up/'deploy'))
sys.dont_write_bytecode=True
builtins.input=lambda *args:'closeConsole'
import play_mujoco
print('ORIGINAL_IMPORT_PASS',flush=True)
p=None
try:
    p=play_mujoco.PlayMujoco()
    print('ORIGINAL_INIT_PASS',json.dumps({'nq':p.mjModel.nq,'nv':p.mjModel.nv,'nu':p.mjModel.nu,'dt':p.mjModel.opt.timestep,'RL_FREQ':p.locomotion_policy.RL_FREQ,'actor_inputs':[(x.name,x.shape) for x in p.locomotion_policy.policy.get_inputs()],'actor_outputs':[(x.name,x.shape) for x in p.locomotion_policy.policy.get_outputs()]}),flush=True)
finally:
    if p is not None:p.viewer.close()

