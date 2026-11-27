"""Immutable source + isolated owner runs. Scope, evidence and exits are explicit."""
import argparse,hashlib,json,os,platform,re,shutil,signal,subprocess,sys,tarfile,time,uuid
from pathlib import Path
from verify_evidence import digest,valid_name,verify
ROOT=Path(__file__).resolve().parents[2]
CH=ROOT/'Ch15'
ORDER=('build','mock','physical_basic','cube','joint','faults')
ROS_IMAGE='ros@sha256:5147d3ae250ce754afd399f6bfec15b33dd4e473ca357e30432a3182031bfad6'
GZ_IMAGE='ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f'
SCENARIOS=('F03_transient','F03_persistent','F04','F06','F01')
class Blocked(Exception):pass
def put(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a],text=True).strip()
def source(pin):
    actual=git('rev-parse','HEAD')
    if not re.fullmatch('[a-f0-9]{40}',pin or '') or actual!=pin:raise Blocked('SOURCE_SHA_DRIFT')
    if git('status','--porcelain','--untracked-files=all','--','Ch15'):raise Blocked('SOURCE_DIRTY')
    lock=json.loads((CH/'dependencies/reuse.audit.json').read_text())
    for path,h in lock['protected_trees'].items():
        if git('rev-parse','HEAD:'+path)!=h:raise Blocked('PROTECTED_TREE_DRIFT:'+path)
    rows=[]
    # Verify bytes against Git blobs even when assume-unchanged or CRLF hides a change.
    for row in subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-rz','HEAD','Ch15']).split(b'\x00'):
        if not row:continue
        meta,name=row.decode().split('\t',1);mode,typ,h=meta.split()
        p=ROOT/name
        if typ!='blob' or mode not in ('100644','100755') or not p.is_file() or p.is_symlink():raise Blocked('SOURCE_PATH_MISSING_OR_UNSAFE:'+name)
        b=p.read_bytes();calc=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\x00'+b).hexdigest()
        if calc!=h:raise Blocked('SOURCE_BLOB_DRIFT:'+name)
        rows.append(dict(path=name,git_blob=h,sha256=hashlib.sha256(b).hexdigest()))
    return dict(result='PASS',requested_sha=pin,actual_sha=actual,protected_trees=lock['protected_trees'],files=rows,bootstrap_sha256=digest(CH/'scripts/bootstrap_ch15.sh'),bootstrap_verified=os.environ.get('CH15_BOOTSTRAP_VERIFIED_SHA256')==digest(CH/'scripts/bootstrap_ch15.sh'))
def pack(run):
    files=[]
    for p in sorted(run.rglob('*')):
        if p.is_symlink():raise ValueError('SYMLINK_IN_EVIDENCE:'+str(p.relative_to(run)))
        if p.is_dir():continue
        n=p.relative_to(run).as_posix()
        if not p.is_file() or not valid_name(n) or n=='manifest.sha256':raise ValueError('UNSAFE_EVIDENCE:'+n)
        files.append((p,n,digest(p)))
    manifest=run/'manifest.sha256';manifest.write_text(''.join(h+'  '+n+'\n' for _,n,h in files))
    arc=run.parent/(run.name+'.evidence.tar.gz');side=arc.with_name(arc.name+'.sha256')
    with tarfile.open(arc,'x:gz',compresslevel=3) as tar:
        for p,n,_ in files+[(manifest,'manifest.sha256','')]:
            tar.add(p,arcname=n,recursive=False)
    side.write_text(digest(arc)+'  '+arc.name+'\n')
    receipt=verify(arc,side)
    put(run.parent/(run.name+'.archive-verification.json'),receipt)
    print('CH15_OWNER_EVIDENCE='+str(arc),flush=True)
    print('CH15_ARCHIVE_SHA256='+receipt['archive_sha256'],flush=True)
    return receipt
def run_logged(cmd,log,env=None,timeout=None):
    with log.open('wb') as f:
        p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=env)
        try:return p.wait(timeout=timeout)
        except BaseException:
            try:os.killpg(p.pid,signal.SIGINT)
            except ProcessLookupError:pass
            try:p.wait(timeout=25)
            except subprocess.TimeoutExpired:
                try:os.killpg(p.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                p.wait()
            raise
def native_inputs(a):
    if not a.acknowledge_assets:raise Blocked('ASSET_ACK_REQUIRED')
    root=os.environ.get('CH15_NATIVE_ROOT','');approval=os.environ.get('CH15_ASSET_APPROVAL','')
    build=os.environ.get('CH13_REUSE_BUILD','');venv=os.environ.get('CH13_REUSE_VENV','')
    if not all(x and Path(x).is_absolute() for x in (root,approval,build,venv)):raise Blocked('NATIVE_ENV_REQUIRED')
    nr,ap,b,v=map(Path,(root,approval,build,venv))
    if not nr.is_dir() or not ap.is_file() or not (v/'bin/python').is_file():raise Blocked('NATIVE_ENV_MISSING')
    if b.resolve().is_relative_to(nr.resolve()) or b.resolve().is_relative_to(ROOT.resolve()):raise Blocked('NATIVE_BUILD_NOT_ISOLATED')
    return nr,ap
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--check',required=True,choices=[*ORDER,'all','icd','design','git','analysis','markers','clock_diag'])
    p.add_argument('--headless',action='store_true');p.add_argument('--scenario',choices=SCENARIOS)
    p.add_argument('--acknowledge-assets',action='store_true');p.add_argument('--bag',type=Path)
    a=p.parse_args()
    pin=os.environ.get('CH15_SOURCE_SHA','')
    work=Path(os.environ.get('CH15_WORK_ROOT',str(Path.home()/'ch15-owner'))).expanduser().resolve()
    if work.is_relative_to(ROOT):print('CH15_BLOCKED_OUTPUT_INSIDE_SOURCE');return 2
    work.joinpath('runs').mkdir(parents=True,exist_ok=True)
    rid=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'_'+uuid.uuid4().hex
    run=work/'runs'/rid;run.mkdir();start=time.time_ns()
    result=dict(run_id=rid,requested_sha=pin,requested_check=a.check,scenario=a.scenario,source='UNVERIFIED',result='FAIL',full_mission_success=False,owner_l3='NOT_REVIEWED',start_wall_ns=start,profiles=[])
    put(run/'environment.json',dict(platform=platform.platform(),python=sys.version,os_release=Path('/etc/os-release').read_text() if Path('/etc/os-release').exists() else '',cpu_count=len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,headless=True))
    put(run/'source-receipt.json',dict(result='NOT_RUN',requested_sha=pin))
    audit=[];rc=1;stage='source'
    def term(signum,frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,term)
    try:
        receipt=source(pin);put(run/'source-receipt.json',receipt);result['source']='PINNED'
        if a.scenario and a.check!='faults':raise Blocked('SCENARIO_ONLY_FAULTS')
        if a.check=='analysis' and (a.bag is None or not a.bag.is_absolute() or not (a.bag/'metadata.yaml').is_file()):raise Blocked('ABSOLUTE_BAG_REQUIRED')
        paths=ORDER if a.check=='all' else (a.check,)
        if 'physical_basic' in paths:
            stage='native_preflight';nr,ap=native_inputs(a)
            adapter=CH/'ros2_ws/src/ch15_adapters/ch15_adapters/ch13_basic_adapter.py'
            ec=run_logged([sys.executable,str(adapter),'preflight','--root',str(nr),'--lock',str(CH/'dependencies/reuse.audit.json'),'--contract',str(CH/'dependencies/ch13_contract.lock.json'),'--approval',str(ap),'--out',str(run/'native-preflight.json')],run/'native-preflight.log')
            if ec:raise Blocked('NATIVE_PREFLIGHT_FAILED')
        if any(x not in ('physical_basic','design','git') for x in paths):
            stage='docker_preflight'
            if not shutil.which('docker') or subprocess.run(['docker','info'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:raise Blocked('DOCKER_UNAVAILABLE')
        for check in paths:
            stage=check;case=run/check;case.mkdir()
            print('CH15_RUN '+check,flush=True)
            if check=='physical_basic':
                # Exact approved G04 V6 runner, no apt/venv mutation by this wrapper.
                code=run_logged(['bash',str(CH/'scripts/run_table_mission.sh'),str(nr),str(ap),str(case/'native-run')],case/'runner.log',timeout=1800)
                if code==0:
                    native=json.loads((case/'native-run/native/basic_result.json').read_text())
                    after=json.loads((case/'native-run/after-verdict.json').read_text())
                    if not (native['source']=='CH15_TABLE_V3_BT' and native['result']=='PASS' and native['full_mission_success'] is False and native['original_native_l2_pass'] is False and len(native['checks'])==10 and all(native['checks'].values()) and after['result']=='PASS'):code=1
                audit.append(dict(profile=check,exit=code,residual='PASS' if code==0 else 'NOT_CONFIRMED'))
            elif check in ('design','git'):
                if check=='design':
                    code=0
                    for test in ('test_scenarios.py','test_world_contract.py'):
                        code=run_logged([sys.executable,'-m','unittest','discover','-s',str(CH/'tests'),'-p',test,'-v'],case/(test+'.log'))
                        if code:break
                else:code=run_logged(['bash',str(CH/'scripts/g05_git_lab.sh')],case/'git.log',timeout=45)
                audit.append(dict(profile=check,exit=code,residual='N/A_NO_ROS'))
            else:
                image=GZ_IMAGE if check=='cube' else ROS_IMAGE
                name='ch15-'+rid.lower().replace('_','-')+'-'+check
                cmd=['docker','run','--rm','--init','--name',name,'--label','ch15.owner.run='+rid,'--shm-size=1g','-v',str(ROOT)+':/repo:ro','-v',str(case)+':/evidence','-e','CH15_FAULT_SCENARIO='+str(a.scenario or '')]
                if check=='analysis':cmd+=['-v',str(a.bag.resolve())+':/input-bag:ro']
                cmd += [image,'bash','/repo/Ch15/scripts/owner_runtime.sh',check]
                code=1;clock_process=None;clock_log=None;clock_exit=None
                try:
                    if check in ('clock_diag','faults'):
                        clock_log=(case/'host-clock.log').open('wb')
                        clock_process=subprocess.Popen([sys.executable,str(CH/'python/clock_diag.py'),'--out',str(case/'host-clock'),'--duration','1300','--scope','wsl_host'],stdout=clock_log,stderr=subprocess.STDOUT,start_new_session=True)
                        deadline=time.monotonic()+5
                        while not (case/'host-clock/samples.jsonl').is_file():
                            if clock_process.poll() is not None or time.monotonic()>deadline:raise RuntimeError('HOST_CLOCK_DIAG_START_FAILED')
                            time.sleep(.02)
                    code=run_logged(cmd,case/'container.log',timeout=1200)
                finally:
                    if clock_process is not None:
                        if clock_process.poll() is None:clock_process.terminate()
                        try:clock_exit=clock_process.wait(timeout=8)
                        except subprocess.TimeoutExpired:
                            clock_process.kill();clock_exit=clock_process.wait();code=1
                        if clock_exit!=0:code=1
                    if clock_log is not None:clock_log.close()
                    # Only inspect/remove this run's uniquely named container.
                    remaining=subprocess.run(['docker','ps','-aq','--filter','name=^/'+name+'$'],capture_output=True,text=True,check=True).stdout.strip()
                    forced=bool(remaining)
                    if forced:subprocess.run(['docker','rm','-f',name],check=False,stdout=subprocess.DEVNULL)
                    residual=subprocess.run(['docker','ps','-aq','--filter','label=ch15.owner.run='+rid],capture_output=True,text=True,check=True).stdout.split()
                    audit.append(dict(profile=check,image=image,exit=code,forced_cleanup=forced,residual_containers=residual,host_clock_exit=clock_exit))
                    if forced or residual:code=1
                if check in ('clock_diag','faults'):
                    diag_files=sorted(case.glob('**/clock-diagnosis.json'))+sorted(case.glob('*/summary.json'))
                    diagnoses=[]
                    for dp in diag_files:
                        d=json.loads(dp.read_text())
                        diagnoses.append(dict(path=str(dp.relative_to(case)),result=d.get('result'),quality=d.get('quality'),observed_system_or_ros_step=d.get('observed_system_or_ros_step')))
                    result['clock_diagnosis']=diagnoses
                    if code==0 and (clock_exit!=0 or not diagnoses):code=1
                if code==0:
                    rr=json.loads((case/'residual.json').read_text())
                    if rr.get('result')!='PASS':code=1
            result['profiles'].append(dict(profile=check,exit=code,result='PASS' if code==0 else 'BLOCKED' if code==2 else 'FAIL'))
            if code==2:raise Blocked('PROFILE_BLOCKED:'+check)
            if code:raise RuntimeError('PROFILE_FAILED:'+check+':'+str(code))
        result['result']='PASS';rc=0
    except Blocked as e:result.update(result='BLOCKED',reason=str(e),first_failed_boundary=stage);rc=2
    except KeyboardInterrupt:result.update(result='CANCELED',reason='operator interrupt',first_failed_boundary=stage);rc=130
    except Exception as e:result.update(result='FAIL',reason=repr(e),first_failed_boundary=stage);rc=1
    finally:
        result.update(exit_code=rc,end_wall_ns=time.time_ns(),physical_full='BLOCKED',physical_fault='BLOCKED_PHYSICAL_FAULT')
        put(run/'process_audit.json',dict(profiles=audit))
        put(run/'owner-result.json',result)
        try:pack(run)
        except Exception as e:print('CH15_ARCHIVE_FAIL '+repr(e),file=sys.stderr);rc=1
        print('CH15_OWNER_RESULT='+json.dumps(result),flush=True)
    return rc
if __name__=='__main__':sys.exit(main())
