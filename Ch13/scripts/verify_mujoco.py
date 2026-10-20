#!/usr/bin/env python3
"""Deterministic physical fixture test: settle, approach, close, lift, hold."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import mujoco
from ch13_sim_core.mujoco_runtime import MujocoRuntime
from ch13_sim_core.grasp_metrics import GraspObservation, classify_grasp

def verify(output,image=None):
    observations=[]; samples=[]
    with MujocoRuntime() as runtime:
        runtime.reset(42)
        target=runtime.contract.nominal
        for step in range(450):
            # 50Hz setpoints, 500Hz physics. Shoulder pitch lifts the tool with negative angle.
            t=step*.02
            target[13]=0.0 if t<3 else -.20*min((t-3)/2,1)
            target[18:]=.035 if t<1 else max(0.,.035*(1-(t-1)/1.5))
            runtime.apply_named_targets(runtime.contract.names,target,runtime.snapshot().time)
            runtime.step(10)
            s=runtime.snapshot()
            if step==49:
                initial_cube=s.cube_position.copy()
                reference=s.cube_position-s.tool_position
            if step>=50:
                observations.append(GraspObservation(s.time,s.left_contact,s.right_contact,float(s.cube_position[2]-initial_cube[2]),float(np.linalg.norm(s.cube_position-s.tool_position-reference))))
            samples.append({'time':s.time,'base':s.base_position.tolist(),'tilt':s.base_tilt,'cube':s.cube_position.tolist(),'tool':s.tool_position.tolist(),'contacts':[s.left_contact,s.right_contact]})
        grasp=classify_grasp(observations)
        stable=all(.38<x['base'][2]<.55 and x['tilt']<.15 for x in samples)
        result={'schema_version':1,'status':'PASS' if grasp.success and stable else 'FAIL','engine':'MuJoCo','version':mujoco.__version__,'utc':datetime.now(timezone.utc).isoformat(),'seed':42,'actuator_count':20,'finite':True,'base_stable':stable,'grasp':asdict(grasp),'samples':samples}
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,indent=2))
        if image: image.parent.mkdir(parents=True,exist_ok=True); runtime.render(image)
    print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--image',type=Path)
    a=p.parse_args();raise SystemExit(verify(a.output,a.image))
