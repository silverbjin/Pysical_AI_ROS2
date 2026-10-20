import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
sys.path.insert(0, str(Path('Ch13/scripts').resolve()))
from verify_vision_13_4 import source_snapshot
output = Path(os.environ['CH13_EGL_EVIDENCE'])/'native-environment.json'
if output.exists():
    raise FileExistsError(output)
external = Path('/home/jinho/ch13_mujoco_ws/src/mujoco_ros2_control')
data = dict(source=source_snapshot(Path.cwd()), euid=os.geteuid(), python=sys.executable,
            platform=platform.platform(), boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            packages={name:importlib.metadata.version(name) for name in ('numpy','torch','ultralytics','mujoco')},
            environment={k:os.environ.get(k) for k in ('ROS_DISTRO','ROS_DOMAIN_ID','MUJOCO_GL','OMP_NUM_THREADS','LP_NUM_THREADS')},
            external_path=str(external))
for key, command in [('external_head',['git','rev-parse','HEAD']),
                     ('external_status',['git','status','--porcelain'])]:
    value = subprocess.run(command,cwd=external,text=True,capture_output=True,check=True)
    data[key] = value.stdout.strip()
weights = Path('/home/jinho/ch13_vision_13_4_assets/yolov8n.pt')
data['weights'] = dict(path=str(weights),sha256=hashlib.sha256(weights.read_bytes()).hexdigest())
assert data['euid'] == 1000
assert data['external_head'] == 'c261f5552edf124d1000a23fb25b6c07cadeb807'
assert not data['external_status']
assert data['weights']['sha256'] == 'f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36'
output.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({k:v for k,v in data.items() if k != 'source'}))
