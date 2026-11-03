"""Candidate B preflight: load released actors, inspect action ownership; no physics stepping."""
import ast,hashlib,json,os,sys
from pathlib import Path
import torch,yaml
here=Path(__file__).resolve().parent;root=here.parents[3];up=root.parent/'upstream-leggedmanip-candidate-b'
src=up/'mujoco/deploy/deploy_mujoco/go2_piper/go2_piper.py'
report={'candidate':'B','commit':'4e12109d1eccb1d9da2e4a35f189fabea3f13677','pid':os.getpid(),'ppid':os.getppid(),'scope':'TorchScript CPU inference + source/config ownership audit; no simulation, no B environment reproduction','policies':[]}
for name in ['config.yaml','config_wbc.yaml']:
 cfg=yaml.safe_load((src.parent/name).read_text())
 path=Path(cfg['policy_path'].replace('{CURRENT_ROOT_DIR}',str(up/'mujoco')))
 actor=torch.jit.load(str(path),map_location='cpu').eval()
 with torch.inference_mode():
  output=actor(torch.zeros(1,210,dtype=torch.float32))
 report['policies'].append({'config':name,'path':path.relative_to(up).as_posix(),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'input_shape':[1,210],'actual_output_shape':list(output.shape),'output_finite':bool(torch.isfinite(output).all()),'num_actions':cfg['num_actions'],'policy_owned_leg_indices':[0,12],'policy_owned_arm_indices':[12,18],'default_arm_target':cfg['default_angles'][12:],'simulation_dt_s':cfg['simulation_dt'],'control_decimation':cfg['control_decimation']})
report['ownership_source_lines']=[{'line':n,'text':s.strip()} for n,s in enumerate(src.read_text().splitlines(),1) if any(term in s for term in ['arm_action  =','action_out  =','target_dof_pos = action_out','data.ctrl[:] = tau'])]
report['preflight_result']='INCOMPATIBLE_WITH_INDEPENDENT_ARM_OWNER_AS_DELIVERED'
report['reason']='Both provided actors command 18 joints, and upstream main applies last six actor outputs to arm PD targets. No delivered independent-arm mode demonstrated. Dropping/replacing those outputs would change the validated closed-loop policy/model contract; not adopted silently.'
(here/'ownership_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
assert all(x['actual_output_shape']==[1,18] and x['output_finite'] for x in report['policies'])
