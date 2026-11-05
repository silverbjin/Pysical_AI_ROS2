"""Candidate GC reproducer from saved owner status; not proof of the live pause."""
import gc,json,sys,time,resource
from pathlib import Path
from ch13_manipulation_reuse.gc_timing import GCTiming
from ch13_manipulation_reuse.planning import Planner
import py_trees
p=Path(__file__).resolve().parent;mode=sys.argv[1];out=p/('owner_status_gc_'+mode+'_v21.json');assert not out.exists()
c=p.parent/'Pysical_AI_ROS2_13_8/Ch13/evidence/section_13_8_system/e0b2d5b0-0678-41e0-87c6-c48793781402'
gc.collect();probe=GCTiming(minimum_s=0.);probe.start();start=time.monotonic();rows=[];status={}
for line in (c/'manipulation_status.jsonl').open():
 status=json.loads(line)
 rows.append(dict(status) if mode=='parsed' else line.rstrip('\n'))
load_s=time.monotonic()-start;automatic=probe.summary();probe.stop();samples=[]
for _ in range(3):
 before=time.monotonic();cpu=time.thread_time();collected=gc.collect(2);samples.append(dict(wall_s=time.monotonic()-before,thread_cpu_s=time.thread_time()-cpu,collected=collected))
report=dict(scope='offline candidate GC experiment with saved status journal; separate process per mode; no robot, ROS publishers or global GC policy changes',mode=mode,rows=len(rows),load_wall_s=load_s,manual_gen2=samples,automatic_gc=automatic,maximum_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,objects_tracked=len(gc.get_objects()),last_status_equal=json.loads(rows[-1])==status if mode=='raw' else rows[-1]==status)
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='automatic_gc'}))