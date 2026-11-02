"""Fresh-process NumPy thread/cost comparison, not ROS or physical acceptance."""
import ctypes,hashlib,json,os,statistics,subprocess,sys,time,uuid
from pathlib import Path
if '--child' in sys.argv:
 import numpy as np
 a=np.array([[.99,-.02,.03,.1],[.02,.99,-.01,-.02],[-.03,.01,.99,.46],[0.,0.,0.,1.]])
 np.linalg.inv(a)
 paths=sorted({r.split()[-1] for r in Path('/proc/self/maps').read_text().splitlines()
  if 'blas' in r.lower() and r.split()[-1].startswith('/')})
 libraries=[]
 for path in paths:
  symbols=subprocess.run(['nm','-D',path],capture_output=True,text=True,check=True).stdout
  candidates=[line.split()[-1] for line in symbols.splitlines() if line.split()
   and line.split()[-1] in ('openblas_get_num_threads','openblas_get_num_threads64_','openblas_get_num_threads_64_')]
  for name in candidates:
   call=getattr(ctypes.CDLL(path),name);call.argtypes=[];call.restype=ctypes.c_int
   libraries.append(dict(path=path,getter=name,threads=call()))
 wall=[];cpu=[]
 for i in range(1000):
  w=time.monotonic_ns();c=time.thread_time_ns();np.linalg.inv(a)
  cpu.append(time.thread_time_ns()-c);wall.append(time.monotonic_ns()-w)
 print(json.dumps(dict(scope='fresh_process_small_affine_inverse_microcomparison_not_engine',
  requested=os.environ.get('OPENBLAS_NUM_THREADS'),numpy=np.__version__,libraries=libraries,
  process_threads=len(list(Path('/proc/self/task').iterdir())),samples=len(wall),
  median_wall_ns=statistics.median(wall),median_thread_ns=statistics.median(cpu),max_wall_ns=max(wall))))
 raise SystemExit(0)
data=[]
for selection in (None,'1'):
 env=dict(os.environ);env.pop('OPENBLAS_NUM_THREADS',None)
 if selection is not None:env['OPENBLAS_NUM_THREADS']=selection
 result=subprocess.run([sys.executable,__file__,'--child'],env=env,capture_output=True,text=True,check=True)
 data.append(json.loads(result.stdout))
out=dict(scope='read_only_thread_ABI_and_microcost_not_engine_causality',
 method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=data)
base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
target=base/('openblas-process-profile-'+str(uuid.uuid4())+'.json')
with target.open('x') as stream:json.dump(out,stream,indent=2)
target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(target),**out),indent=2))
