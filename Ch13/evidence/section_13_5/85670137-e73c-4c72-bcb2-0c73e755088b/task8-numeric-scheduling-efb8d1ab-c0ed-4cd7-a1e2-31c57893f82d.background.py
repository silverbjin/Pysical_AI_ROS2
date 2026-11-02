"""Short cooperative owned arithmetic load; no ROS, persistent settings or I/O."""
import json,os,select,sys,time
mask=json.loads(sys.argv[1]);os.sched_setaffinity(0,mask)
print(json.dumps(dict(ready=True,pid=os.getpid(),affinity=sorted(os.sched_getaffinity(0)))),flush=True)
if sys.stdin.buffer.read(1)!=b'g':raise SystemExit(1)
deadline=time.clock_gettime(time.CLOCK_MONOTONIC_RAW)+8.;value=1
while time.clock_gettime(time.CLOCK_MONOTONIC_RAW)<deadline:
    for _ in range(8192):value=(value*1664525+1013904223)&0xffffffff
    if select.select([sys.stdin],[],[],0)[0]:
        if sys.stdin.buffer.read(1)!=b'g':break
print(json.dumps(dict(stopped=True,pid=os.getpid(),value=value)),flush=True)
