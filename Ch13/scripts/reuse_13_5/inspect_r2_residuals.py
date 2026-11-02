from pathlib import Path
import fcntl,json,sys,os
report=Path(sys.argv[1]);found=[]
modules={'ch13_navigation_reuse.command_gateway','ch13_navigation_reuse.platform_adapter'}
for p in Path('/proc').glob('[0-9]*'):
 try:
  args=(p/'cmdline').read_bytes().split(b'\0');args=[x.decode(errors='replace') for x in args if x]
  if any(x in modules for x in args) or (args and args[0].endswith('/ch13_reuse_wire/ingress')) or any(x.endswith('/run_r2_probe.py') for x in args):
   found.append({'pid':int(p.name),'args':args})
 except (FileNotFoundError,PermissionError,ProcessLookupError):pass
root=Path(__file__).resolve().parents[3]
with (root.parent/'ch13_reuse_engine.lock').open('a+') as f:
 try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);free=True
 except BlockingIOError:free=False
result={'owned_stack_matches':found,'engine_lock_free':free,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'result':'PASS' if not found and free else 'FAIL'}
report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert result['result']=='PASS'
