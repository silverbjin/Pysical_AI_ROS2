#!/usr/bin/env bash
set -e
cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
source .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/env-native.sh
python - <<'PY'
import json,os,uuid,numpy,scipy.linalg,ctypes
from pathlib import Path
base=Path(os.environ['CH13_NAV_EVIDENCE'])
libraries={line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'openblas' in line and '/' in line}
loaded=[]
for filename in sorted(libraries):
    item=dict(path=filename)
    library=ctypes.CDLL(filename)
    for symbol in ('openblas_get_num_threads','openblas_get_num_threads64_'):
        try:fn=getattr(library,symbol)
        except AttributeError:continue
        fn.argtypes=[];fn.restype=ctypes.c_int;item.update(symbol=symbol,num_threads=fn());break
    loaded.append(item)
v=dict(scope='fresh_unit_process_configuration_not_failure_instant_or_runtime',
 env={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')},
 loaded_libraries=loaded,process_threads=len(list(Path('/proc/self/task').iterdir())),pid=os.getpid())
path=base/f'task8-unit-numeric-threads-{uuid.uuid4()}.json'
path.write_text(json.dumps(v,indent=2)+'\n')
path.with_suffix('.method.sh').write_bytes(Path('.superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/inspect-test-numeric-threads.sh').read_bytes())
print(path);print(json.dumps(v))
PY
