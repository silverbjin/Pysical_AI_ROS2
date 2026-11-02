"""One owned JSON/file process; immutable private IPC, bounded and fail closed."""
import json
import multiprocessing as mp
import os
from pathlib import Path
import pickle
from queue import Full
import time


class JournalFailure(RuntimeError):
    """Evidence failed; independent ROS cleanup must remain usable."""


FIELDS = ('submitted', 'written', 'outstanding_records', 'outstanding_bytes',
          'peak_records', 'peak_bytes', 'write_wall_ns', 'write_cpu_ns',
          'max_write_wall_ns', 'accepting', 'actual_json_bytes')
INDEX = {name: index for index, name in enumerate(FIELDS)}


def _wire_bound(value):
    """Conservative ensure_ascii JSON bytes; never use pickle's memoized size."""
    if value is None:return 4
    if isinstance(value, bool):return 5
    if isinstance(value, int):return abs(value).bit_length()//3+3
    if isinstance(value, float):return 32
    if isinstance(value, str):return 12*len(value)+2
    if isinstance(value, (list, tuple)):return 2+sum(_wire_bound(v)+2 for v in value)
    if isinstance(value, dict):
        if any(not isinstance(k,str) for k in value):raise TypeError('string record keys required')
        return 2+sum(_wire_bound(k)+_wire_bound(v)+4 for k,v in value.items())
    raise TypeError('unsupported private record value: '+type(value).__name__)


def _set_error(error, message):
    if not error.value:error.value=message.encode('utf-8',errors='replace')[:2047]


def _writer(path, queue, condition, counts, error, owner, ready):
    failure=None
    try:
        stat=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()
        with condition:
            owner[:]=[os.getpid(),os.getppid(),os.getuid(),os.getpgrp(),int(stat[19])]
        with Path(path).open('a',encoding='utf-8') as sink:
            ready.set()
            while True:
                item=queue.get()
                if item is None:break
                payload,bound=item
                start,cpu=time.monotonic_ns(),time.thread_time_ns()
                # Only bytes created by our parent encode() enter this private
                # pipe. Never deserialize network messages or external files.
                value=pickle.loads(payload)
                encoded=json.dumps(value,allow_nan=False)+'\n'
                actual=len(encoded.encode('utf-8'))
                if actual>bound:raise ValueError('JSON exceeded reserved wire bound')
                if sink.write(encoded)!=len(encoded):raise OSError('short observation write')
                elapsed,used=time.monotonic_ns()-start,time.thread_time_ns()-cpu
                with condition:
                    counts[INDEX['written']]+=1
                    counts[INDEX['outstanding_records']]-=1
                    counts[INDEX['outstanding_bytes']]-=bound
                    counts[INDEX['write_wall_ns']]+=elapsed
                    counts[INDEX['write_cpu_ns']]+=used
                    counts[INDEX['max_write_wall_ns']]=max(counts[INDEX['max_write_wall_ns']],elapsed)
                    counts[INDEX['actual_json_bytes']]+=actual
                    condition.notify_all()
            sink.flush()
    except BaseException as exc:
        failure=repr(exc)
        with condition:
            _set_error(error,failure);counts[INDEX['accepting']]=0;condition.notify_all()
    finally:
        ready.set()
    if failure:raise SystemExit(1)


class ProcessJournal:
    def __init__(self,path,*,max_records=256,max_bytes=8*1024*1024):
        if type(max_records) is not int or type(max_bytes) is not int or min(max_records,max_bytes)<=0:
            raise ValueError('positive journal capacity required')
        self.path=Path(path).resolve(strict=True)
        if (not self.path.is_file() or self.path.stat().st_size or self.path.stat().st_uid!=os.getuid()):
            raise ValueError('owned empty journal file required')
        ctx=mp.get_context('spawn')
        self.condition=ctx.Condition(ctx.RLock())
        self.counts=ctx.Array('q',len(FIELDS),lock=False);self.counts[INDEX['accepting']]=1
        self.error_text=ctx.Array('c',2048,lock=False);self.owner=ctx.Array('q',5,lock=False)
        self.queue=ctx.Queue(maxsize=max_records);self.ready=ctx.Event()
        self.max_records,self.max_bytes=max_records,max_bytes
        self.pending={};self.stop_sent=False;self.ipc_closed=False;self.failure_saved=False
        self.process=ctx.Process(target=_writer,args=(str(self.path),self.queue,self.condition,
            self.counts,self.error_text,self.owner,self.ready),name='navigation_evidence_encoder')
        self.process.start()
        if not self.ready.wait(5.):
            with self.condition:_set_error(self.error_text,'encoder startup unconfirmed')
        try:
            with self.condition:self._check()
        except JournalFailure:
            # Never hold the shared counter lock while waiting for the child.
            self.close(timeout_sec=5.)
            raise

    @staticmethod
    def encode(value):
        bound=_wire_bound(value)+1
        return pickle.dumps(value,protocol=5),bound

    def _check(self):
        if self.process.exitcode is not None and not self.stop_sent and not self.error_text.value:
            _set_error(self.error_text,'encoder exited before close: '+str(self.process.exitcode))
        if self.error_text.value:
            raise JournalFailure('observation journal failed: '+self.error_text.value.decode('utf-8'))

    def submit(self,item):
        if (type(item) is not tuple or len(item)!=2 or type(item[0]) is not bytes
                or type(item[1]) is not int or item[1]<=0):raise TypeError('immutable private record required')
        with self.condition:
            self._check()
            if not self.counts[INDEX['accepting']]:raise RuntimeError('observation journal closed')
            bound=item[1]
            if (self.counts[INDEX['outstanding_records']]>=self.max_records
                    or self.counts[INDEX['outstanding_bytes']]+bound>self.max_bytes):
                _set_error(self.error_text,'journal capacity exceeded')
                self.counts[INDEX['accepting']]=0;self._check()
            try:self.queue.put_nowait(item)
            except Full:
                _set_error(self.error_text,'journal capacity exceeded');self.counts[INDEX['accepting']]=0;self._check()
            written=self.counts[INDEX['written']]
            self.pending={seq:data for seq,data in self.pending.items() if seq>written}
            self.counts[INDEX['submitted']]+=1
            self.pending[self.counts[INDEX['submitted']]]=item
            self.counts[INDEX['outstanding_records']]+=1;self.counts[INDEX['outstanding_bytes']]+=bound
            for current,peak in (('outstanding_records','peak_records'),('outstanding_bytes','peak_bytes')):
                self.counts[INDEX[peak]]=max(self.counts[INDEX[peak]],self.counts[INDEX[current]])

    def flush(self,*,timeout_sec=5.):
        deadline=time.monotonic()+timeout_sec
        with self.condition:
            target=self.counts[INDEX['submitted']]
            while self.counts[INDEX['written']]<target:
                self._check();remaining=deadline-time.monotonic()
                if remaining<=0:raise RuntimeError('journal flush unconfirmed')
                self.condition.wait(min(.05,remaining))
            self._check()

    def close(self,*,timeout_sec=5.):
        deadline=time.monotonic()+timeout_sec
        with self.condition:self.counts[INDEX['accepting']]=0
        if not self.stop_sent and self.process.is_alive():
            try:self.queue.put(None,timeout=max(0.,deadline-time.monotonic()));self.stop_sent=True
            except Full:raise RuntimeError('journal close queue unconfirmed')
        self.process.join(timeout=max(0.,deadline-time.monotonic()))
        if self.process.is_alive():raise RuntimeError('journal process not joined; resources retained')
        with self.condition:
            if self.process.exitcode!=0:_set_error(self.error_text,'encoder exit: '+str(self.process.exitcode))
            if self.counts[INDEX['written']]!=self.counts[INDEX['submitted']]:
                _set_error(self.error_text,'journal record count differs')
            if self.error_text.value and not self.failure_saved:
                remaining={seq:item for seq,item in self.pending.items() if seq>self.counts[INDEX['written']]}
                if remaining:
                    with self.path.with_suffix('.unwritten.pickle').open('xb') as sink:pickle.dump(remaining,sink,protocol=5)
                self.failure_saved=True
            if not self.ipc_closed:
                # A failed consumer can leave the feeder blocked. All pending
                # immutable originals above are retained; never report success.
                if self.error_text.value:self.queue.cancel_join_thread()
                self.queue.close()
                if not self.error_text.value:self.queue.join_thread()
                self.ipc_closed=True
            self._check()

    def report(self):
        with self.condition:
            values={name:self.counts[index] for name,index in INDEX.items()}
            values['accepting']=bool(values['accepting'])
            return dict(**values,max_records=self.max_records,max_bytes=self.max_bytes,
                scope='owned_process_encoding_and_file_write',encoding='owned_process_json',
                outstanding_bytes_scope='conservative_original_JSON_wire_upper_bound',
                error=self.error_text.value.decode('utf-8') or None,
                joined=self.process.exitcode is not None,process_exitcode=self.process.exitcode,
                owner=dict(zip(('pid','ppid','uid','pgid','start_ticks'),self.owner[:])))
