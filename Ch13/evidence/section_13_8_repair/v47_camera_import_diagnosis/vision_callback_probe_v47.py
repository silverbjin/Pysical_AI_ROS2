"""One-off isolated observer measurement, no live action or lease authority."""
import os,sys,builtins,time
from pathlib import Path
root=Path(os.environ['CH13_PROBE_ROOT'])
for name in ('ch13_navigation_reuse','ch13_manipulation_reuse','ch13_system_validation'):
 sys.path.insert(0,str(root/'Ch13/ros2_ws/src'/name))
from ch13_navigation_reuse.callback_timing import CallbackTiming,timed_callback
from ch13_navigation_reuse.vision_approach import VisionObserver,main
import_rows=[]
original_import=builtins.__import__
def measured_import(name,*args,**kwargs):
 if name!='ch13_manipulation_reuse.cylinder_vision':return original_import(name,*args,**kwargs)
 start=time.monotonic();cpu=time.thread_time()
 try:return original_import(name,*args,**kwargs)
 finally:
  end=time.monotonic()
  if not import_rows or end-start>.01:import_rows.append(dict(name=name,start_wall=start,end_wall=end,cpu_s=time.thread_time()-cpu))
builtins.__import__=measured_import
if os.environ.get('CH13_PROBE_PRELOAD_CYLINDER')=='1':
 from ch13_manipulation_reuse.cylinder_vision import fit_cylinder
original_init=VisionObserver.__init__
def initialize(self,*args,**kwargs):
 original_init(self,*args,**kwargs);self.callback_timing=CallbackTiming(limit=16384)
VisionObserver.__init__=initialize
VisionObserver.native=timed_callback('vision.native',channel_index=0)(VisionObserver.native)
VisionObserver.packet=timed_callback('vision.packet',channel_index=1)(VisionObserver.packet)
VisionObserver.tick=timed_callback('vision.tick')(VisionObserver.tick)
original_diagnostics=VisionObserver.diagnostics
def diagnostics(self):
 result=original_diagnostics(self);result['callback_timing']=self.callback_timing.summary();result['cylinder_import_spans']=import_rows;result['preloaded']=os.environ.get('CH13_PROBE_PRELOAD_CYLINDER')=='1';return result
VisionObserver.diagnostics=diagnostics
main()
