"""Approved service/tick comparison; normal-user parent owns one durable lease."""
import hashlib,json,os,select,signal,subprocess,sys,time,uuid
from pathlib import Path
from temporary_clock_lease import ClockLease
from clock_convergence import ClockConvergence

repo=Path.cwd().resolve();task=Path(__file__).resolve().parent
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
wsl='/mnt/c/Windows/System32/wsl.exe'
powershell='/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
assert os.getuid()==1000 and (repo/'Ch13').is_dir()
service_only='--service-only' in sys.argv
root=base/(('clock-single-owner-' if service_only else 'clock-normalization-')+str(uuid.uuid4()));root.mkdir()
for name in ('temporary-clock-session.py','temporary_clock_lease.py','test_temporary_clock_lease.py',
             'clock-tick-control.c','read-clock-discipline.c','timesync-comparison-user.sh',
             'clock_convergence.py','test_clock_convergence.py'):
    (root/name).write_bytes((task/name).read_bytes())
binary=root/'clock-tick-control';reader=root/'clock-reader'
subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',str(root/'clock-tick-control.c'),'-o',str(binary)],check=True)
subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',str(root/'read-clock-discipline.c'),'-o',str(reader)],check=True)
metadata=dict(scope='user_approved_temporary_shared_tick_and_two_services_not_engine_acceptance',
    pid=os.getpid(),uid=os.getuid(),restoration_pending=False,restored=False,validation_exit=None,
    changes={'services':['Ubuntu-22.04:systemd-timesyncd.service','Ubuntu-24.04:systemd-timesyncd.service'],
             'adjtimex_write_modes':'ADJ_TICK only','temporary_tick_us':10000,'sets_current_time':False,
             'changes_freq_status_driver_or_permanent_settings':False},commands=[],phases=[])
if service_only:
    metadata['scope']='approved_two_services_only_unmodified_chrony_convergence_not_engine_acceptance'
    metadata['changes'].update(adjtimex_write_modes='none',temporary_tick_us=None)
metadata['source_and_binary_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
    for p in root.iterdir() if p.is_file()}
safety=repo/(task/'clock-safety-run.txt').read_text().strip()
for name in ('red.log','green.log','red-command.json','green-command.json','test_red.py','lease_red.py','lease_green.py',
             'single-owner-red.log','single-owner-green.log','single-owner-red-command.json','single-owner-green-command.json'):
    (root/('safety-'+name)).write_bytes((safety/name).read_bytes())
def durable(path,data):
    temp=path.with_suffix('.tmp')
    with temp.open('w') as stream:
        json.dump(data,stream,indent=2);stream.flush();os.fsync(stream.fileno())
    temp.replace(path)
def save():durable(root/'session.json',metadata)
def command(args,allow=(0,)):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
    metadata['commands'].append(dict(command=args,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr));save()
    if p.returncode not in allow:raise RuntimeError('command failed: '+repr(args)+' '+p.stderr)
    return p.stdout.strip()
class Ops:
    def inspect(self,distro):
        clock=json.loads(command([wsl,'-d',distro,'-u','jinho','--',str(binary),'read']))
        active=command([wsl,'-d',distro,'-u','jinho','--','systemctl','is-active','systemd-timesyncd.service'],(0,3))
        enabled=command([wsl,'-d',distro,'-u','jinho','--','systemctl','is-enabled','systemd-timesyncd.service'])
        return dict(active=active,enabled=enabled,boot=clock['boot_id'],namespace=clock['time_namespace'],clock_ticks=clock['clock_ticks'])
    def clock(self):return json.loads(command([str(binary),'read']))
    def service(self,distro,action):command([wsl,'-d',distro,'-u','root','--','systemctl',action,'systemd-timesyncd.service'])
    def set_tick(self,expected,target,boot):
        command([wsl,'-d','Ubuntu-24.04','-u','root','--',str(binary),'set-tick',str(expected),str(target),boot])
ops=Ops()
def save_lease(record):
    durable(root/'lease.json',record)
    metadata['restoration_pending']=record['restoration_pending'];metadata['restored']=record['restored'];save()
lease=ClockLease(ops,save_lease,normalize_tick=not service_only)
abort=[False];children=[]
def interrupted(signum,frame):abort[0]=True
signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
def owned_runtimes():
    names=(b'run_navigation_13_5.py',b'mujoco_node',b'mujoco_ros2_control_node',b'gz sim',b'crawl_controller',b'split_observer_13_5.py')
    rows=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit() or int(path.name)==os.getpid():continue
        try:
            c=path.joinpath('cmdline').read_bytes()
            if path.stat().st_uid==os.getuid() and any(n in c for n in names):rows.append(dict(pid=int(path.name),command=c.replace(bytes([0]),b' ').decode(errors='replace')))
        except (ProcessLookupError,FileNotFoundError,PermissionError):continue
    return rows
def wait_child(child,*,interrupt=True):
    sent=False
    while child.poll() is None:
        if abort[0] and interrupt and not sent:
            os.killpg(child.pid,signal.SIGINT);sent=True
        time.sleep(.05)
    return child.wait()
def cross_clock():
    expression='[Console]::WriteLine("READY"); while(($line=[Console]::ReadLine()) -ne $null) { if($line -eq "stop") { break }; [Console]::WriteLine((@{qpc=[Diagnostics.Stopwatch]::GetTimestamp();frequency=[Diagnostics.Stopwatch]::Frequency;utc=[DateTimeOffset]::UtcNow.ToString("o")} | ConvertTo-Json -Compress)) }'
    server_command=[powershell,'-NoLogo','-NoProfile','-NonInteractive','-Command',expression]
    server=subprocess.Popen(server_command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    children.append(server);metadata['qpc_server_command']=server_command;save()
    def response():
        if not select.select([server.stdout],[],[],5.)[0]:raise RuntimeError('owned QPC reply deadline')
        line=server.stdout.readline().strip()
        if not line:raise RuntimeError('owned QPC server closed')
        return line
    if response()!='READY':raise RuntimeError('owned QPC startup not confirmed')
    rows=[];start=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
    with (root/'cross-clock.jsonl').open('x') as output:
        for index in range(7):
            while time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)-start<index*10_000_000_000:
                if abort[0]:raise RuntimeError('interrupted before engines')
                time.sleep(.05)
            a=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW);ma=time.monotonic_ns();ra=time.time_ns()
            server.stdin.write('sample\n');server.stdin.flush();host=json.loads(response())
            rb=time.time_ns();mb=time.monotonic_ns();b=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
            row=dict(raw_before_ns=a,raw_after_ns=b,mono_before_ns=ma,mono_after_ns=mb,
                     realtime_before_ns=ra,realtime_after_ns=rb,host=host)
            rows.append(row);output.write(json.dumps(row)+'\n');output.flush()
    server.stdin.write('stop\n');server.stdin.flush();server.stdin.close()
    metadata['qpc_server_exit']=server.wait(timeout=10);save()
    if server.returncode:raise RuntimeError('owned QPC server failed')
    first,last=rows[0],rows[-1]
    assert len({r['host']['frequency'] for r in rows})==1
    host_elapsed=(last['host']['qpc']-first['host']['qpc'])/first['host']['frequency']
    rates={}
    for name,low,high in (('raw','raw_before_ns','raw_after_ns'),('monotonic','mono_before_ns','mono_after_ns'),('realtime','realtime_before_ns','realtime_after_ns')):
        rates[name]=[(last[low]-first[high])/1e9/host_elapsed,(last[high]-first[low])/1e9/host_elapsed]
    passed=all(.99<=lo<=hi<=1.01 for lo,hi in rates.values())
    report=dict(scope='diagnostic_admission_not_engine_acceptance',host_elapsed_seconds=host_elapsed,
                ratio_intervals=rates,passed=passed)
    durable(root/'cross-clock-result.json',report);print(json.dumps(report),flush=True)
    if not passed:raise RuntimeError('host/guest original clock rates differ; no engine')

def observe_convergence():
    gate=ClockConvergence();count=0
    with (root/'convergence.jsonl').open('x') as output:
        while gate.state=='WAITING':
            clock=ops.clock()
            a=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
            mono=time.monotonic_ns();real=time.time_ns()
            b=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
            state=gate.observe((a+b)//2,mono,real,clock['tick_us'])
            count+=1;output.write(json.dumps(dict(raw_before_ns=a,raw_after_ns=b,mono_ns=mono,
                real_ns=real,clock=clock,state=state,stable_since=gate.stable_since,last_ratio=gate.last_ratio))+'\n');output.flush()
            if abort[0]:raise RuntimeError('interrupted before engines')
            if state=='WAITING':time.sleep(1.)
    result=dict(scope='additional_read_only_convergence_not_replacement_for_original_preflight',
        state=gate.state,reason=gate.reason,raw_deadline_seconds=180,quiet_seconds=40,samples=count,
        changes_chrony_or_kernel=False,passed=gate.state=='READY')
    durable(root/'convergence-result.json',result);print(json.dumps(result),flush=True)
    if not result['passed']:raise RuntimeError('unmodified clock convergence failed; no engine')

save();print(json.dumps(dict(clock_normalization=str(root),uid=os.getuid())),flush=True)
exit_code=1
try:
    metadata['initial_related_runtimes']=owned_runtimes();save()
    if metadata['initial_related_runtimes']:raise RuntimeError('existing runtime; no system mutation')
    # Real negative checks run unprivileged and must never write.
    negative=subprocess.run([str(binary),'set-tick','9166','10000','wrong-boot'],capture_output=True,text=True)
    metadata['negative_guard']=dict(returncode=negative.returncode,output=negative.stderr);save()
    if negative.returncode!=3:raise RuntimeError('ownership guard failed; no system mutation')
    lease.begin();metadata['phases'].append('services_only_stopped' if service_only else 'normalized_confirmed');save()
    if service_only:observe_convergence()
    with (root/'original-clocks.jsonl').open('x') as output:
        capture=subprocess.Popen([str(reader)],stdout=output,start_new_session=True);children.append(capture)
        cross_error=None
        try:cross_clock()
        except BaseException as error:cross_error=error
        if wait_child(capture)!=0:raise RuntimeError('original clock recorder failed; no engine')
        metadata['phases'].append('original_clock_recording_closed');save()
        if cross_error is not None:raise cross_error
    # Continuous 150s read-only witness must also have no >1ms REALTIME steps.
    previous=None;steps=[];maximum_tick=set()
    with (root/'original-clocks.jsonl').open() as source:
        for line in source:
            row=json.loads(line)
            if 'monotonic_ns' not in row:continue
            maximum_tick.add(row['tick_us']);offset=row['realtime_ns']-row['monotonic_ns']
            if previous is not None and abs(offset-previous)>1_000_000:steps.append(dict(raw_ns=row['raw_before_ns'],step_ns=offset-previous))
            previous=offset
    witness=dict(ticks=sorted(maximum_tick),steps=steps,passed=maximum_tick=={10000} and not steps)
    durable(root/'continuous-clock-result.json',witness)
    if not witness['passed'] or abort[0]:raise RuntimeError('original clock witness failed/interrupted; no engine')
    metadata['phases'].append('rate_and_continuity_admitted');save()
    seed='/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence/native-g1-mujoco-9d296bc8-1f99-494a-83f4-2bfc0bdc3751/result.json'
    cmd=['bash',str(root/'timesync-comparison-user.sh'),str(root),seed]
    metadata['validation_command']=cmd;save()
    child=subprocess.Popen(cmd,start_new_session=True);children.append(child)
    exit_code=wait_child(child);metadata['validation_exit']=exit_code;save()
except BaseException as error:
    metadata['failure']=repr(error);save();print('COMPARISON_FAILURE',repr(error),flush=True)
finally:
    # Do not change the clock under a still-running owned engine on interruption.
    for child in children:
        if child.poll() is None:
            if child.stdin is not None and not child.stdin.closed:
                try:child.stdin.write('stop\n');child.stdin.flush();child.stdin.close()
                except (BrokenPipeError,OSError):pass
            wait_child(child)
    deadline=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)+60_000_000_000
    residual=owned_runtimes()
    while residual and time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)<deadline:
        time.sleep(.2);residual=owned_runtimes()
    metadata['final_related_runtimes']=residual;save()
    if residual:
        metadata['failure']='owned runtime cleanup unconfirmed; retain restoration-pending lease';save()
    else:lease.close()
    metadata['final_clock']=ops.clock()
    metadata['final_services']={d:ops.inspect(d) for d in ClockLease.DISTROS};save()
    print(json.dumps(dict(clock_normalization=str(root),restored=metadata['restored'],
        validation_exit=metadata['validation_exit'],failure=metadata.get('failure'))),flush=True)
if not metadata['restored']:raise SystemExit('restoration unconfirmed; no next engine')
raise SystemExit(exit_code)
