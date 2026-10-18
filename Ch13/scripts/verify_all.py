#!/usr/bin/env python3
"""Fresh serial verification, never a cached evidence-to-PASS converter."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
CH=ROOT/'Ch13'

def source_inventory(root):
    result={}
    for directory,dirs,names in os.walk(root):
        dirs[:]=[d for d in dirs if d not in ('.venv','evidence','__pycache__','.pytest_cache','dist','build') and not d.endswith('.egg-info') and not (Path(directory).name=='ros2_ws' and d.startswith(('build','install','log')))]
        for name in names:
            p=Path(directory)/name
            result[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
    return result

def summarize(results):
    if any(results.get(k,{}).get('returncode')!=0 for k in ('tests','build','ros_tests')):return 'FAIL'
    if any(results.get(k,{}).get('status')!='PASS' for k in ('mujoco','mujoco_ros','gazebo')):return 'FAIL'
    return 'PASS' if results['gazebo'].get('physical_grasp',{}).get('status')=='PASS' else 'PARTIAL'

def verify():
    evidence=CH/'evidence';evidence.mkdir(exist_ok=True)
    results={};commands=[]
    def run(key,args,cwd=ROOT,extra_env=None):
        env=os.environ.copy();env.update(extra_env or {})
        log=evidence/(key+'.log');start=time.time()
        with log.open('w') as output:
            process=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=output,stderr=subprocess.STDOUT)
        commands.append({'name':key,'command':list(map(str,args)),'cwd':str(cwd),'returncode':process.returncode,'started_unix':start,'ended_unix':time.time(),'log':str(log.relative_to(CH))})
        results[key]={'returncode':process.returncode}
        print(key,process.returncode,flush=True)
        return process.returncode
    run('build',[sys.executable,'/usr/bin/colcon','--log-base','log13_1','build','--build-base','build13_1','--install-base','install13_1','--symlink-install'],CH/'ros2_ws')
    run('tests',[sys.executable,'-m','pytest','tests','ros2_ws/src/ch13_control/test','-q'],CH)
    run('ros_tests',[sys.executable,'/usr/bin/colcon','--log-base','log13_1','test','--build-base','build13_1','--install-base','install13_1','--return-code-on-test-failure'],CH/'ros2_ws')
    for key,script,args,env in [
        ('mujoco','verify_mujoco.py',['--output',evidence/'mujoco/result.json','--image',evidence/'mujoco/frame.png'],{'MUJOCO_GL':'egl'}),
        ('mujoco_ros','ros_probe.py',['--backend','mujoco','--output',evidence/'mujoco/ros-result.json'],{'ROS_DOMAIN_ID':'181'}),
        ('gazebo','gazebo_probe.py',['--output',evidence/'gazebo/result.json'],{'ROS_DOMAIN_ID':'182','GZ_PARTITION':'ch13_verify_'+str(os.getpid())})]:
        run(key,[sys.executable,CH/'scripts'/script,*args],extra_env=env)
        path=evidence/('gazebo/result.json' if key=='gazebo' else ('mujoco/ros-result.json' if key=='mujoco_ros' else 'mujoco/result.json'))
        # Stale files cannot promote a failed or nonexecuted verifier.
        if results[key]['returncode']==0 and path.is_file() and path.stat().st_mtime>=commands[-1]['started_unix']-1:
            results[key]=json.loads(path.read_text())
        else:results[key]['status']='FAIL'
    git=lambda *args:subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
    earlier=git('diff','--name-only','1451f54a64374f2ff150a39429cc89e9e3b07696','--',*[f'Ch{i:02}' for i in range(5,13)])
    results['earlier_chapters_unchanged']=not earlier
    hashes={'Ch13/'+p:digest for p,digest in source_inventory(CH).items()}
    summary={'schema_version':1,'status':summarize(results) if not earlier else 'FAIL','utc':datetime.now(timezone.utc).isoformat(),'verified_code_commit':git('rev-parse','HEAD'),'worktree_status':git('status','--short'),'python':platform.python_version(),'commands':commands,'results':{k:{a:b for a,b in v.items() if a not in ('samples','base_samples','grasp_samples')} if isinstance(v,dict) else v for k,v in results.items()},'source_sha256':hashes,'policy_smoke':'UNVERIFIED: source manifest exists but no committed model ZIP weights','limits':['Gazebo fixture grasp is separate from integration status','No MoveIt2, integrated ros2_control, stable PPO, transport or real robot validation']}
    (evidence/'verification_summary.json').write_text(json.dumps(summary,indent=2))
    print('status:',summary['status'],flush=True)
    return 0 if summary['status'] in ('PASS','PARTIAL') else 1

if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    raise SystemExit(verify())
