"""Owned foreground session, not a daemon or a service/clock controller."""
import hashlib,json,os,select,subprocess,sys,tempfile,time,uuid
from pathlib import Path


def _identity():
    def ticks(path):return int(Path(path).read_text().rsplit(')',1)[1].split()[19])
    return dict(uid=os.getuid(),pid=os.getpid(),start_ticks=ticks('/proc/self/stat'),
        init_start_ticks=ticks('/proc/1/stat'),
        machine_sha256=hashlib.sha256(Path('/etc/machine-id').read_bytes()).hexdigest(),
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        namespace=os.readlink('/proc/self/ns/time'),clock_ticks=os.sysconf('SC_CLK_TCK'),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


def guarded_service(action,expected,current,invoke):
    if action not in ('start','stop') or current.get('uid')!=0:
        raise RuntimeError('only approved privileged service start/stop')
    if any(current.get(key)!=expected.get(key) for key in ('boot','init_start_ticks','machine_sha256')):
        raise RuntimeError('service target init/boot/machine changed; no operation')
    return invoke(['systemctl',action,'systemd-timesyncd.service'])


def serve(nonce):
    initial=_identity()
    def emit(op,**values):print(json.dumps(dict(op=op,nonce=nonce,**values)),flush=True)
    emit('ready',identity=initial)
    try:
        for line in sys.stdin:
            command=json.loads(line)
            if command.get('nonce')!=nonce:raise RuntimeError('foreground session nonce')
            identity=_identity()
            if identity!=initial:raise RuntimeError('foreground session/init identity changed')
            op=command.get('op')
            if op=='close':emit('closed',identity=identity);return 0
            if op!='inspect':raise RuntimeError('foreground session command')
            result=subprocess.run(['systemctl','show','systemd-timesyncd.service',
                '--property=ActiveState','--property=UnitFileState','--property=MainPID'],
                capture_output=True,text=True,timeout=3.)
            if result.returncode:raise RuntimeError('service status read failed')
            fields=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
            snapshot=dict(identity,active=fields['ActiveState'],enabled=fields['UnitFileState'],
                service_main_pid=int(fields['MainPID']),inspected_wall_ns=time.monotonic_ns())
            emit('inspect',snapshot=snapshot)
        raise RuntimeError('foreground session parent EOF without close')
    except BaseException as error:
        emit('error',error=repr(error));return 1


class DistroSession:
    def __init__(self,prefix,*,label,directory):
        self.nonce=str(uuid.uuid4());self.directory=Path(directory).resolve(strict=True)
        if not label.replace('-','').replace('_','').isalnum():raise ValueError('session label')
        self.label=label;self.identity=None;self.joined=False;self.closed=False;self.close_acknowledged=False
        self.error=None;self.stderr=tempfile.TemporaryFile();self.stderr_path=None;self.stderr_bytes=0
        self.buffer=b'';self.rpc=(self.directory/(label+'-session.jsonl')).open('x')
        self.command=[*prefix,str(Path(__file__).resolve()),'--serve',self.nonce]
        self.process=subprocess.Popen(self.command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=self.stderr,start_new_session=True)
        try:
            value=self._receive(30.)
            if value.get('op')!='ready':raise RuntimeError('foreground session not ready')
            identity=value['identity']
            if (identity['uid']!=os.getuid() or identity['pid']<=0 or identity['init_start_ticks']<=0
                    or identity['source_sha256']!=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()):
                raise RuntimeError('foreground session ownership/source mismatch')
            self.identity=identity
        except BaseException:
            self.close()
            raise

    def _receive(self,timeout):
        deadline=time.monotonic()+timeout
        while b'\n' not in self.buffer:
            remaining=deadline-time.monotonic()
            if remaining<=0 or not select.select([self.process.stdout],[],[],remaining)[0]:
                raise RuntimeError('session response deadline')
            block=os.read(self.process.stdout.fileno(),4096)
            if not block:raise RuntimeError('session response EOF')
            self.buffer+=block
            if len(self.buffer)>65536:raise RuntimeError('session response capacity')
        line,self.buffer=self.buffer.split(b'\n',1)
        value=json.loads(line)
        self.rpc.write(json.dumps(dict(received_wall_ns=time.monotonic_ns(),response=value))+'\n');self.rpc.flush()
        if value.get('nonce')!=self.nonce:raise RuntimeError('session response nonce')
        if value.get('op')=='error':raise RuntimeError(value.get('error','session failure'))
        return value

    def check(self):
        if self.closed or self.error or self.process.poll() is not None:
            raise RuntimeError('foreground session closed/failed; no replacement allowed')

    def inspect(self):
        self.check()
        self.process.stdin.write((json.dumps(dict(nonce=self.nonce,op='inspect'))+'\n').encode());self.process.stdin.flush()
        result=self._receive(5.)
        if result.get('op')!='inspect':raise RuntimeError('session inspect acknowledgement')
        value=result['snapshot']
        if any(value.get(key)!=old for key,old in self.identity.items()):
            raise RuntimeError('session/init identity changed')
        return value

    def close(self):
        if self.closed:
            if self.error:raise RuntimeError(self.error)
            return
        try:
            if self.process.poll() is not None:raise RuntimeError('foreground session exited before close')
            self.process.stdin.write((json.dumps(dict(nonce=self.nonce,op='close'))+'\n').encode());self.process.stdin.flush()
            response=self._receive(5.)
            if response.get('op')!='closed' or response.get('identity')!=self.identity:
                raise RuntimeError('session close acknowledgement/identity')
            self.close_acknowledged=True
        except BaseException as error:self.error=repr(error)
        try:
            self.process.wait(timeout=5.);self.joined=True
        except subprocess.TimeoutExpired:
            self.error=self.error or 'foreground session join deadline; resources retained'
            raise RuntimeError(self.error) from None
        self.closed=True
        if self.process.returncode or not self.close_acknowledged:self.error=self.error or 'session exit not confirmed'
        self.process.stdin.close();self.process.stdout.close()
        self.rpc.close()
        self.stderr_bytes=os.fstat(self.stderr.fileno()).st_size
        if self.stderr_bytes:
            self.stderr.seek(0);path=self.directory/(self.label+'-session.stderr')
            with path.open('xb') as out:
                while block:=self.stderr.read(65536):out.write(block)
            self.stderr_path=str(path)
        self.stderr.close()
        if self.error:raise RuntimeError(self.error)

    def report(self):
        return dict(command=self.command,identity=self.identity,proxy_pid=self.process.pid,
            joined=self.joined,returncode=self.process.poll(),close_acknowledged=self.close_acknowledged,
            error=self.error,stderr_bytes=self.stderr_bytes,stderr_file=self.stderr_path,
            scope='owned_unprivileged_foreground_no_service_clock_or_distro_configuration_changes')


if __name__=='__main__':
    if len(sys.argv)==6 and sys.argv[1]=='--service-action':
        expected=dict(boot=sys.argv[3],init_start_ticks=int(sys.argv[4]),machine_sha256=sys.argv[5])
        guarded_service(sys.argv[2],expected,_identity(),lambda command:subprocess.run(command,check=True))
        print(json.dumps(dict(action=sys.argv[2],confirmed_instance=expected)),flush=True)
        raise SystemExit(0)
    if len(sys.argv)!=3 or sys.argv[1]!='--serve':raise SystemExit(2)
    raise SystemExit(serve(sys.argv[2]))
