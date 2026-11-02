"""Closed-input G1 measure/IK cost; no ROS initialization or motor output."""
import sys,json,time,ctypes,hashlib,statistics
from pathlib import Path
import numpy as np
root=Path.cwd();src=root/'Ch13/ros2_ws/src/integrated_robot_navigation';sys.path.insert(0,str(src))
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.scene import load_scene
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.samples import SensorBundle,Sample
trial='native-g1-gazebo-330b055b-0cb9-4db5-872d-06e2613fe447'
base=root/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
report_path=base/trial/'controller_report.json';r=json.loads(report_path.read_text());s=r['first_fault']
scene=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/(trial+'-prepared')/'scene'
model=compile_model(Path(load_scene('gazebo',scene)['robot']['path']).read_text());assert model.model_sha256==r['model_sha256']
bundle=SensorBundle(**{k:Sample(**v) if v else None for k,v in s['samples'].items()})
m=CrawlMachine(model,default_limits());m.reference_body=np.array(s['reference_body']);m._targets={f:np.array(v) for f,v in s['targets'].items()}
def step():
    q,_,_,_,_,com=m._measure(bundle,s['ros_ns'],s['wall_ns'])
    return dict(targets=m._solve(q,False),com=com)
first=step();blas=[]
for lib in sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'openblas' in line and '.so' in line}):
    dll=ctypes.CDLL(lib)
    for symbol in ('openblas_get_num_threads64_','openblas_get_num_threads'):
        if hasattr(dll,symbol):
            fn=getattr(dll,symbol);fn.restype=ctypes.c_int;fn.argtypes=[]
            blas.append(dict(library=lib,symbol=symbol,threads=fn()))
costs=[]
for _ in range(120):
    start=time.perf_counter_ns();cpu=time.thread_time_ns();result=step()
    costs.append(dict(wall_ns=time.perf_counter_ns()-start,cpu_ns=time.thread_time_ns()-cpu))
out=dict(scope='closed_G1_measure_IK_arithmetic_not_engine',model_sha256=model.model_sha256,
    report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),blas=blas,
    process_threads=len(list(Path('/proc/self/task').iterdir())),samples=costs,
    output=dict(targets=result['targets'],com=list(result['com'])),
    method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
path=base/sys.argv[1];assert not path.exists();path.write_text(json.dumps(out,indent=2))
print(json.dumps(dict(path=str(path),blas=blas,process_threads=out['process_threads'],
    median_wall_ns=statistics.median(v['wall_ns'] for v in costs),max_wall_ns=max(v['wall_ns'] for v in costs),
    median_cpu_ns=statistics.median(v['cpu_ns'] for v in costs))))
