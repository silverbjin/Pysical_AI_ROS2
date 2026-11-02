"""Cold versus initialized response-path READY; no rate acceptance decision."""
import hashlib,json,select,subprocess,time,uuid
from pathlib import Path
from qpc_protocol import server_expression
base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
trials=[]
for warm in (False,True,True,False):
    command=['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
        '-NoLogo','-NoProfile','-NonInteractive','-Command',server_expression(warm=warm)]
    p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    def read():
        if not select.select([p.stdout],[],[],5.)[0]:raise RuntimeError('owned host QPC deadline')
        return p.stdout.readline().strip()
    try:
        if read()!='READY':raise RuntimeError('owned QPC not ready')
        rows=[]
        for index in range(3):
            a=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
            p.stdin.write('sample\n');p.stdin.flush();host=json.loads(read())
            b=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
            rows.append(dict(index=index,raw_before_ns=a,raw_after_ns=b,roundtrip_ns=b-a,host=host))
    finally:
        p.stdin.write('stop\n');p.stdin.flush();p.stdin.close();p.wait(timeout=5.)
        stderr=p.stderr.read();p.stdout.close();p.stderr.close()
    if p.returncode or stderr:raise RuntimeError('owned QPC process failed: '+stderr)
    trials.append(dict(warm_ready=warm,command=command,rows=rows,exit=p.returncode))
target=base/('qpc-ready-'+str(uuid.uuid4())+'.json')
out=dict(scope='owned_readonly_host_handshake_not_clock_rate_or_engine_acceptance',trials=trials,
    protocol_sha256=hashlib.sha256(Path(__file__).with_name('qpc_protocol.py').read_bytes()).hexdigest())
with target.open('x') as stream:json.dump(out,stream,indent=2)
target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
target.with_suffix('.protocol.py').write_bytes(Path(__file__).with_name('qpc_protocol.py').read_bytes())
print(json.dumps(dict(path=str(target),trials=[dict(warm_ready=r['warm_ready'],
    roundtrip_ms=[v['roundtrip_ns']/1e6 for v in r['rows']],exit=r['exit']) for r in trials]),indent=2))
