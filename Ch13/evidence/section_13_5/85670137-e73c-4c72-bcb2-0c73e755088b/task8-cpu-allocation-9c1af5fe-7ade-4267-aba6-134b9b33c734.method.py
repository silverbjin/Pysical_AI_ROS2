"""Read only current user CPU allocation; no priority/affinity/quota writes."""
import hashlib,json,os,platform,resource,uuid
from pathlib import Path
result=dict(scope='current_post_trial_cpu_allocation_not_historical_scheduler_trace',
    pid=os.getpid(),uid=os.getuid(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    kernel=platform.release(),cpu_count=os.cpu_count(),affinity=sorted(os.sched_getaffinity(0)),
    nice=os.getpriority(os.PRIO_PROCESS,0),rtprio_limit=resource.getrlimit(resource.RLIMIT_RTPRIO),
    cgroup=Path('/proc/self/cgroup').read_text(),settings={},cgroups=[])
for name in ('/sys/devices/system/cpu/online','/sys/devices/system/cpu/offline','/proc/loadavg','/proc/pressure/cpu'):
    path=Path(name)
    if path.is_file():result['settings'][name]=path.read_text().strip()
for line in result['cgroup'].splitlines():
    if not line.startswith('0::'):continue
    root=Path('/sys/fs/cgroup');path=root/line[3:].lstrip('/')
    while path==root or root in path.parents:
        values={}
        for key in ('cpu.max','cpu.stat','cpu.weight','cpuset.cpus.effective'):
            entry=path/key
            if entry.is_file():values[key]=entry.read_text().strip()
        result['cgroups'].append(dict(path=str(path),values=values))
        if path==root:break
        path=path.parent
result['method_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
out=base/('task8-cpu-allocation-'+str(uuid.uuid4())+'.json');assert not out.exists()
out.write_text(json.dumps(result,indent=2));out.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(out),**result),indent=2))
