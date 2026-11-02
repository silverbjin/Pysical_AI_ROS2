"""Serial owned G2 run using the EXACT completed G1 scene and installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

parser=argparse.ArgumentParser();parser.add_argument('--g1-result',required=True)
parser.add_argument('--scenario',choices=('crawl-cycle','crawl-reverse'),default='crawl-cycle')
parser.add_argument('--archive-from-native',action='store_true')
args=parser.parse_args();repo=Path.cwd().resolve()
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b')
assert native.resolve()==native and native.stat().st_uid==os.getuid()
proof=Path(args.g1_result).resolve(strict=True);g1=json.loads(proof.read_text())
assert g1['gate']=='G1' and g1['status']=='PASS' and g1['engine'] in ('mujoco','gazebo')
assert all(g1['checks'].get(key) is True for key in g1['required_checks'])
prior=json.loads((proof.parent/'teardown.json').read_text())
assert prior['parent_reaped'] and not prior['forced_cleanup'] and prior['residual_live_pids']==[]
profiles=[value.split(':=',1)[1] for value in g1['command'] if value.startswith('carry_profile:=')]
assert len(profiles)==1
profile=Path(profiles[0]).resolve(strict=True)
scene=Path(g1['scene']['robot']['path']).resolve(strict=True).parent
engine=g1['engine'];key=str(uuid.uuid4());name=f'native-g2-{engine}-{key}'
output=native/'evidence'/name;destination=base/name
assert not output.exists() and not destination.exists()
command=[sys.executable,'Ch13/scripts/run_navigation_13_5.py','--engine',engine,
    '--scenario',args.scenario,'--scene-dir',str(scene),'--profile',str(profile),
    '--g1-result',str(proof),'--output-dir',str(output),
    '--control-clock-mode',g1['execution_mode']['control_clock'],
    '--dart-contact-mode',g1['execution_mode']['dart_contact'],
    '--observer-backend',g1['execution_mode'].get('observer_backend','python')]
driver=native/'evidence'/('g2-driver-'+key+'.log')
environment=dict(os.environ)
for name_key in ('ROS_DOMAIN_ID','MUJOCO_GL','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','LP_NUM_THREADS'):
    value=g1.get('environment',{}).get(name_key)
    if value is None:environment.pop(name_key,None)
    else:environment[name_key]=str(value)
print(json.dumps(dict(native_output=str(output),repository_copy=str(destination),g1_result=str(proof),
    reused_scene=str(scene),scenario=args.scenario,command=command)),flush=True)
with driver.open('x') as log:
    process=subprocess.run(command,env=environment,stdout=log,stderr=subprocess.STDOUT)
result=json.loads((output/'result.json').read_text());teardown=json.loads((output/'teardown.json').read_text())
reaped=(teardown.get('parent_reaped') is True or result.get('engine_started') is False)
residual=teardown.get('residual_live_pids',[])
if not reaped or residual:raise RuntimeError('owned cleanup unconfirmed; no copy/next engine')
from archive_native_storage import export_closed
export=export_closed(output,destination,native/'evidence',archive_large=args.archive_from_native)
def sha(path):
    value=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):value.update(block)
    return value.hexdigest()
files=export['files']
shutil.copyfile(driver,base/('task8-g2-driver-'+key+'.log'))
ledger=dict(**export,g1_result=str(proof),g1_result_sha256=sha(proof),
    reused_scene=str(scene),scenario=args.scenario,command=command,runner_returncode=process.returncode,
    storage_method_sha256=sha(Path(__file__).with_name('archive_native_storage.py')),
    tool_sha256=sha(Path(__file__)))
with (destination/'storage-copy-ledger.json').open('x') as file:json.dump(ledger,file,indent=2)
print(json.dumps(dict(path=str(destination),status=result['status'],runner_returncode=process.returncode,
    forced_cleanup=teardown.get('forced_cleanup'),residual=residual)),flush=True)
raise SystemExit(process.returncode)
