"""One numerical child, bounded local protocol; no ROS or motor authority.

Configure/close may wait. The control path only sends one bounded packet and
polls once without blocking. The explicit same-cycle transaction additionally
allows one event wait within a10ms total transaction cap. Kernel computation keeps its original10ms cap;
transport/result collection has a separate two-control-period 40ms deadline.
Explicit event_receiver collects complete frames independently of model ticks.
"""
import argparse
from contextlib import ExitStack
import copy
import hashlib
import json
import os
import select
import signal
import socket
import struct
import subprocess
import sys
import time
import numpy as np

MAX_FRAME=131072
MAX_JOB=32768
DISPATCH_NS=40_000_000
CONSUMPTION_NS=200_000_000
TRANSACTION_NS=10_000_000


def assess_numeric_close(record,model_sha256):
    """Lifecycle evidence only; a mathematical/task failure stays a failure."""
    return bool(isinstance(record,dict)
        and record.get('scope')=='one_numerical_job_no_command_authority'
        and record.get('model_sha256')==model_sha256
        and type(record.get('pid')) is int and record['pid']>0
        and type(record.get('owner_pid')) is int and record['owner_pid']>0
        and record['pid']!=record['owner_pid']
        and all(record.get(k) is True for k in ('closed','acknowledged','parent_reaped'))
        and all(record.get(k) is False for k in ('pending','forced_cleanup'))
        and record.get('receipt_mode','model_poll') in ('model_poll','event_receiver')
        and (record.get('receipt_mode')!='event_receiver' or
            record.get('receiver_joined') is True and record.get('receiver_slot_empty') is True)
        and (record.get('command_space')!='stance_xyz' or
            record.get('kernel_backend')=='native_complete_1'
            and record.get('complete_kernel_abi')==1
            and all(record.get(k) is True for k in ('reference_geometry_closed','optimizer_closed','complete_kernel_closed')))
        and type(record.get('returncode')) is int and record['returncode']==0
        and record.get('error')=='')


def assess_numeric_jobs(record):
    """A clean process exit cannot erase failed or unaccounted computation."""
    return bool(isinstance(record,dict)
        and all(type(record.get(k)) is int and record[k]>=0
            for k in ('submitted','completed','discarded','failed'))
        and record['submitted']>0 and record['completed']>0
        and record['submitted']==record['completed']+record['discarded']
        and record['failed']==0 and record.get('fault')=='' and record.get('pending') is False)


def _packet(value):
    def convert(item):
        if isinstance(item,np.ndarray):return item.tolist()
        if isinstance(item,np.generic):return item.item()
        raise TypeError('non-numeric transport object')
    body=json.dumps(value,allow_nan=False,separators=(',',':'),default=convert).encode()
    if not 0<len(body)<=MAX_FRAME:raise ValueError('bounded numerical frame required')
    return struct.pack('<I',len(body))+body


def _read_exact(channel,size):
    result=b''
    while len(result)<size:
        part=channel.recv(size-len(result))
        if not part:
            if not result:return None
            raise ValueError('partial numerical frame')
        result+=part
    return result


def _blocking_message(channel):
    header=_read_exact(channel,4)
    if header is None:return None
    size=struct.unpack('<I',header)[0]
    if not 0<size<=MAX_FRAME:raise ValueError('numerical frame size')
    body=_read_exact(channel,size)
    if body is None:raise ValueError('missing numerical payload')
    return json.loads(body)


class SpatialLoadProcess:
    asynchronous=True

    def __init__(self,model,*,expected_library_sha256=None,command_space='height',limits=None,
                 expected_reference_library_sha256=None,expected_optimizer_library_sha256=None,
                 receipt_mode='model_poll'):
        from .load_transition import SpatialLoadTransition
        if command_space not in ('height','stance_xyz'):raise ValueError('unknown numerical command space')
        if receipt_mode not in ('model_poll','event_receiver'):raise ValueError('unknown numerical receipt mode')
        self.receipt_mode=receipt_mode;self._receipts=None
        if command_space=='stance_xyz':
            from .carry_profile import _validate_limits
            from .native_reference import reference_library_path
            from .native_xyz import optimizer_library_path
            _validate_limits(limits)
            if expected_reference_library_sha256 is None:
                expected_reference_library_sha256=hashlib.sha256(reference_library_path().read_bytes()).hexdigest()
            if expected_optimizer_library_sha256 is None:
                expected_optimizer_library_sha256=hashlib.sha256(optimizer_library_path().read_bytes()).hexdigest()
        self.command_space=command_space;self._limits=copy.deepcopy(limits)
        self.gains=SpatialLoadTransition(model).gains  # immutable verified geometry only
        self._urdf=model.urdf;self._model_sha=model.model_sha256
        self._expected_library_sha=expected_library_sha256
        self._expected_reference_sha=expected_reference_library_sha256
        self._expected_optimizer_sha=expected_optimizer_library_sha256
        self._process=None;self._channel=None;self._buffer=b'';self._pending=None
        self._ready=None;self._fault='';self._closed=False;self._close_report=None
        self._next=0;self._submitted=0;self._completed=0;self._discarded=0;self._failed=0
        self.preparation=None;self.last_model=None;self.last_attempt=None
        self.last_input=None;self.last_context=None;self.last_input_id=None
        self._last_reply=None;self.last_transaction=None

    def prepare(self):
        if self._closed:raise ValueError('numerical worker closed')
        if self._fault:raise ValueError('numerical worker latched: '+self._fault)
        if self._ready is not None:return copy.deepcopy(self._ready)
        parent,child=socket.socketpair()
        self._channel=parent
        try:
            self._process=subprocess.Popen([sys.executable,'-m',__name__,'--worker-fd',str(child.fileno())],
                pass_fds=(child.fileno(),),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        except OSError as error:
            parent.close();child.close();self._channel=None;self._fault='spawn failed: '+str(error)
            raise ValueError('numerical worker preparation: '+self._fault) from error
        child.close();parent.settimeout(5.)
        try:
            parent.sendall(_packet(dict(kind='init',urdf=self._urdf,command_space=self.command_space,limits=self._limits)))
            ready=_blocking_message(parent)
            if (not isinstance(ready,dict) or ready.get('kind')!='ready' or ready.get('ok') is not True
                    or ready.get('model_sha256')!=self._model_sha
                    or ready.get('pid')!=self._process.pid
                    or ready.get('command_space')!=self.command_space
                    or self.command_space=='stance_xyz'
                    and (ready.get('reference_library_sha256')!=self._expected_reference_sha
                        or ready.get('optimization_library_sha256')!=self._expected_optimizer_sha
                        or ready.get('optimization_backend')!='qpmad_1_5_1_native'
                        or ready.get('kernel_backend')!='native_complete_1'
                        or ready.get('complete_kernel_abi')!=1
                        or ready.get('force_objective')!='bounded_terminal_force')
                    or self._expected_library_sha is not None
                    and ready.get('library_sha256')!=self._expected_library_sha):
                raise ValueError('numerical worker preparation rejected: '+str(ready)[:512])
            if parent.getsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF)<2*MAX_JOB:
                raise ValueError('numerical transport buffer too small')
            self._ready=ready;self.preparation=ready['preparation']
            parent.setblocking(False)
            if self.receipt_mode=='event_receiver':
                from .numeric_receipts import NumericReceiptInbox
                self._receipts=NumericReceiptInbox(parent,self._receive_once)
                self._receipts.start()
            return copy.deepcopy(ready)
        except BaseException as error:
            self._fault=str(error)
            if self._receipts is not None:self._receipts.stop(1.)
            parent.close()
            try:self._process.wait(timeout=2.)
            except subprocess.TimeoutExpired:pass
            raise ValueError('numerical worker preparation: '+str(error)) from error

    def _send(self,value):
        payload=_packet(value)
        if len(payload)>MAX_JOB:raise ValueError('bounded numerical job required')
        try:count=self._channel.send(payload)
        except OSError as error:
            self._fault='transport send: '+str(error)
            raise ValueError('transition optimization worker '+self._fault) from error
        if count!=len(payload):
            self._fault='partial transport send';self._channel.close()
            raise ValueError('transition optimization worker '+self._fault)
        return json.loads(payload[4:])  # the exact JSON value sent, with owned arrays

    def submit(self,args,context):
        if self._closed:raise ValueError('numerical worker closed')
        if self._fault:raise ValueError('numerical worker latched: '+self._fault)
        if self._ready is None:raise ValueError('numerical worker not prepared')
        if self._pending is not None:raise ValueError('one outstanding numerical job required')
        identifier=self._next+1
        issued=time.monotonic_ns()
        sent=self._send(dict(kind='job',id=identifier,args=args))
        self._next=identifier;self._submitted+=1
        self._pending=dict(id=identifier,context=copy.deepcopy(context),
            submitted_wall_ns=issued,discarded=False,numeric_input=sent['args'])
        self.last_input=copy.deepcopy(sent['args']);self.last_context=copy.deepcopy(context)
        self.last_input_id=identifier
        self.last_model=None;self.last_attempt=None
        return identifier

    def transact(self,args,context):
        """One current-snapshot job within10ms; no retry or pipelined request.

        Only the model owner calls this. Independent sensor ingress and the
        single complete-frame reader continue while its Condition releases
        the GIL. The original kernel/receipt/consumption checks still apply.
        """
        if self._fault:raise ValueError('numerical worker latched: '+self._fault)
        if self._receipts is None:raise ValueError('same-cycle transaction requires event receiver')
        if self._pending is not None:raise ValueError('same-cycle transaction requires empty pending slot')
        started=time.monotonic_ns();self.last_transaction=None
        try:
            self.submit(args,context)
            remaining=TRANSACTION_NS-(time.monotonic_ns()-started)
            if remaining<=0 or not self._receipts.wait_message(remaining/1e9):
                raise ValueError('same-cycle transaction deadline')
            if time.monotonic_ns()-started>TRANSACTION_NS:
                raise ValueError('same-cycle transaction deadline')
            reply=self.poll()
            wall=time.monotonic_ns()-started
            if reply is None or wall>TRANSACTION_NS:raise ValueError('same-cycle transaction deadline')
            self.last_transaction=dict(scope='single_current_snapshot_transaction',wall_ns=wall,
                deadline_ns=TRANSACTION_NS,job_id=reply['job_id'])
            return reply
        except (ValueError,OSError) as error:
            self.last_transaction=dict(scope='single_current_snapshot_transaction',
                wall_ns=time.monotonic_ns()-started,deadline_ns=TRANSACTION_NS,error=str(error))
            self.discard();self._fault=str(error)
            raise ValueError('transition optimization worker: '+str(error)) from error

    def _message(self):
        if len(self._buffer)>=4:
            size=struct.unpack('<I',self._buffer[:4])[0]
            if not 0<size<=MAX_FRAME:raise ValueError('numerical result frame size')
            if len(self._buffer)>=size+4:
                body=self._buffer[4:4+size];self._buffer=self._buffer[4+size:]
                return json.loads(body)
        return None

    def _receive_once(self):
        message=self._message()
        if message is not None:return message
        try:chunk=self._channel.recv(MAX_FRAME+4)
        except BlockingIOError:return None
        if not chunk:raise ValueError('numerical worker disconnected')
        self._buffer+=chunk
        if len(self._buffer)>2*(MAX_FRAME+4):raise ValueError('numerical receive buffer bound')
        return self._message()

    def poll(self,*,now_wall_ns=None):
        if self._ready is not None and not self._closed and self._process.poll() is not None:
            self._fault='numerical worker exited before close'
            raise ValueError('transition optimization worker: '+self._fault)
        if self._pending is None:return None
        if self._fault:raise ValueError('numerical worker latched: '+self._fault)
        now=time.monotonic_ns() if now_wall_ns is None else now_wall_ns
        try:
            job=self._pending
            if not job['discarded'] and now<job['submitted_wall_ns']:
                raise ValueError('transition optimization dispatch deadline')
            if self._receipts is not None:
                complete=self._receipts.take()
                if complete is None:
                    if not job['discarded'] and not 0<=now-job['submitted_wall_ns']<=DISPATCH_NS:
                        raise ValueError('transition optimization dispatch deadline')
                    return None
                message,received=complete
            else:
                if not job['discarded'] and not 0<=now-job['submitted_wall_ns']<=DISPATCH_NS:
                    raise ValueError('transition optimization dispatch deadline')
                message=self._receive_once()
                if message is None:return None
                received=time.monotonic_ns()
            if message.get('kind')!='result' or message.get('id')!=job['id']:
                raise ValueError('numerical result identity mismatch')
            consumed=max(now,time.monotonic_ns()) if self._receipts is not None else received
            # Identity has been validated and the frame has been consumed.
            # Retire its transport lifetime even when it is too late to use.
            # Otherwise close can receive STOPPED with a permanently pending
            # job whose sole reply was already removed from the stream.
            self._pending=None;self.last_attempt=message.get('attempt')
            self._last_reply=dict(id=job['id'],submitted_wall_ns=job['submitted_wall_ns'],
                poll_started_wall_ns=now,received_wall_ns=received,
                computed_wall_ns=message.get('computed_wall_ns'),ok=message.get('ok') is True,
                numeric_error=None if message.get('ok') is True else str(message.get('error','numerical result failed')),
                dispatch_deadline_ns=DISPATCH_NS,receipt_mode=self.receipt_mode,
                consumed_wall_ns=consumed)
            if message.get('ok') is not True:self._failed+=1
            if not job['discarded'] and not 0<=received-job['submitted_wall_ns']<=DISPATCH_NS:
                self._discarded+=1;job['discarded']=True
                raise ValueError('transition optimization dispatch deadline')
            if (self._receipts is not None and not job['discarded']
                    and not 0<=consumed-job['submitted_wall_ns']<=CONSUMPTION_NS):
                self._discarded+=1;job['discarded']=True
                raise ValueError('transition optimization consumed result wall age')
            if message.get('ok') is not True:
                raise ValueError(str(message.get('error','numerical result failed')))
            if job['discarded']:return None
            self._completed+=1;self.last_model=message['model']
            return dict(delta=message['delta'],context=job['context'],job_id=job['id'],
                submitted_wall_ns=job['submitted_wall_ns'],received_wall_ns=received,
                computed_wall_ns=message['computed_wall_ns'],numeric_input=job['numeric_input'])
        except (ValueError,OSError,json.JSONDecodeError) as error:
            self._fault=str(error)
            raise ValueError('transition optimization worker: '+str(error)) from error

    def discard(self):
        if self._pending is not None and not self._pending['discarded']:
            self._pending['discarded']=True;self._discarded+=1

    def snapshot(self):
        ready=self._ready or {}
        return dict(scope='one_numerical_job_no_command_authority',
            command_space=self.command_space,optimization_backend=ready.get('optimization_backend'),
            kernel_backend=ready.get('kernel_backend'),complete_kernel_abi=ready.get('complete_kernel_abi'),
            force_objective=ready.get('force_objective'),
            optimization_library_sha256=ready.get('optimization_library_sha256'),
            reference_library_sha256=ready.get('reference_library_sha256'),
            library_sha256=ready.get('library_sha256'),
            pid=None if self._process is None else self._process.pid,
            alive=self._process is not None and self._process.poll() is None,
            submitted=self._submitted,completed=self._completed,discarded=self._discarded,failed=self._failed,
            last_reply=None if self._last_reply is None else dict(self._last_reply),last_input_id=self.last_input_id,
            pending=self._pending is not None,fault=self._fault,closed=self._closed,
            receipt_mode=self.receipt_mode,receipt_inbox=self.receipt_snapshot(),
            last_transaction=copy.deepcopy(self.last_transaction))

    def receipt_snapshot(self):
        return None if self._receipts is None else self._receipts.snapshot()

    def close(self):
        if self._close_report is not None:
            if self._ready is not None and (not self._close_report['acknowledged']
                    or self._close_report['returncode']!=0 or self._close_report.get('error')
                    or self._close_report['pending']):
                raise RuntimeError('numerical worker normal close unconfirmed: '+str(self._close_report))
            return dict(self._close_report)
        self._closed=True;self.discard();ack=False;error='';reference_closed=None;optimizer_closed=None;complete_closed=None
        if self._process is None:
            self._close_report=dict(self.snapshot(),scope='numerical_worker_not_started',
                no_process_started=True,acknowledged=False,parent_reaped=False,
                returncode=None,forced_cleanup=False)
            return dict(self._close_report)
        until=time.monotonic()+2.;stored=None;receiver_joined=self._receipts is None
        try:
            if self._receipts is not None:
                receiver_joined=self._receipts.stop(max(0.,until-time.monotonic()))
                if not receiver_joined:raise ValueError('numerical receipt reader not joined')
                stored=self._receipts.take()
            if self._ready is not None:
                self._send(dict(kind='stop'))
                while time.monotonic()<until and not ack:
                    if stored is not None:message,_=stored;stored=None
                    else:message=self._receive_once()
                    if message is None:
                        select.select([self._channel],[],[],min(.02,max(0.,until-time.monotonic())))
                        continue
                    if message.get('kind')=='stopped':
                        reference_closed=message.get('reference_geometry_closed')
                        optimizer_closed=message.get('optimizer_closed')
                        complete_closed=message.get('complete_kernel_closed')
                        if self.command_space=='stance_xyz' and (reference_closed is not True
                                or optimizer_closed is not True or complete_closed is not True):
                            raise ValueError('numerical reference/optimizer/complete kernel release unconfirmed')
                        ack=True
                    elif message.get('kind')=='result' and self._pending is not None and message.get('id')==self._pending['id']:
                        self.last_attempt=message.get('attempt');self._pending=None
                        if message.get('ok') is not True:
                            self._failed+=1;self._fault=str(message.get('error','numerical result failed'))
                    else:raise ValueError('numerical close message identity')
            self._process.wait(timeout=max(.001,until-time.monotonic()))
        except (ValueError,OSError,subprocess.TimeoutExpired) as failure:error=repr(failure)
        finally:
            if self._channel is not None:self._channel.close()
        code=self._process.poll();stderr=''
        if code is not None and self._process.stderr is not None:
            stderr=self._process.stderr.read(4096).decode(errors='replace');self._process.stderr.close()
        self._close_report=dict(self.snapshot(),acknowledged=ack,parent_reaped=code is not None,
            returncode=code,forced_cleanup=False,error=error,stderr_tail=stderr,
            receipt_mode=self.receipt_mode,receiver_joined=receiver_joined,
            receiver_slot_empty=self._receipts is None or not self._receipts.snapshot()['slot_full'],
            reference_geometry_closed=reference_closed,optimizer_closed=optimizer_closed,
            complete_kernel_closed=complete_closed)
        if self._ready is not None and (not ack or code!=0 or error or self._pending is not None):
            raise RuntimeError('numerical worker normal close unconfirmed: '+str(self._close_report))
        return dict(self._close_report)


def _worker_main(fd):
    # Deliberately no rclpy.init, simulator, time/force setter or publisher.
    # Runtime group SIGINT is handled by the ROS owner. Keep this numerical
    # child alive for its owner's explicit stop/ACK or transport EOF. SIGTERM
    # is unchanged; it cannot masquerade as an acknowledged normal close.
    signal.signal(signal.SIGINT,signal.SIG_IGN)
    from .model import compile_model
    from .native_mass import NativeMassEvaluator
    from .load_transition import SpatialLoadTransition
    with socket.socket(fileno=fd) as channel:
        try:
            init=_blocking_message(channel)
            if init is None or init.get('kind')!='init':raise ValueError('numerical initialization required')
            model=compile_model(init['urdf'])
            with NativeMassEvaluator(model) as core, ExitStack() as resources:
                space=init.get('command_space')
                if space=='height':kernel=SpatialLoadTransition(model,terms_evaluator=core.contact_terms)
                elif space=='stance_xyz':
                    from .native_complete_xyz import CompleteXYZTransition
                    kernel=CompleteXYZTransition(model,init['limits'],native_mass=core)
                    resources.callback(kernel.close)
                else:raise ValueError('explicit numerical command space required')
                preparation=kernel.prepare()
                channel.sendall(_packet(dict(kind='ready',ok=True,scope='numerical_child_no_ros_or_commands',
                    pid=os.getpid(),model_sha256=model.model_sha256,
                    library_sha256=core.provenance['library_sha256'],preparation=preparation,command_space=space,
                    optimization_backend='qpmad_1_5_1_native' if space=='stance_xyz' else None,
                    kernel_backend='native_complete_1' if space=='stance_xyz' else None,
                    complete_kernel_abi=1 if space=='stance_xyz' else None,
                    force_objective=kernel.force_objective if space=='stance_xyz' else None,
                    optimization_library_sha256=kernel._optimizer.provenance['library_sha256'] if space=='stance_xyz' else None,
                    reference_library_sha256=kernel.geometry.provenance['library_sha256'] if space=='stance_xyz' else None)))
                last=0
                while True:
                    message=_blocking_message(channel)
                    if message is None:return 0  # parent transport lifetime ended
                    if message.get('kind')=='stop':
                        resources.close();core.close()
                        channel.sendall(_packet(dict(kind='stopped',
                            optimizer_closed=not kernel._optimizer._finalize.alive if space=='stance_xyz' else None,
                            complete_kernel_closed=kernel.complete_kernel_closed if space=='stance_xyz' else None,
                            reference_geometry_closed=not kernel.geometry._finalize.alive if space=='stance_xyz' else None)))
                        return 0
                    if (message.get('kind')!='job' or type(message.get('id')) is not int
                            or message['id']<=last):raise ValueError('numerical request identity')
                    last=message['id']
                    try:
                        delta=kernel.step(**message['args'])
                        reply=dict(kind='result',id=last,ok=True,delta=delta,model=kernel.last_model)
                    except Exception as error:
                        reply=dict(kind='result',id=last,ok=False,error=str(error)[:512])
                    reply.update(attempt=kernel.last_attempt,computed_wall_ns=time.monotonic_ns())
                    channel.sendall(_packet(reply))
        except Exception as error:
            try:channel.sendall(_packet(dict(kind='ready',ok=False,error=repr(error)[:512])))
            except OSError:pass
            return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--worker-fd',type=int,required=True)
    raise SystemExit(_worker_main(parser.parse_args().worker_fd))
