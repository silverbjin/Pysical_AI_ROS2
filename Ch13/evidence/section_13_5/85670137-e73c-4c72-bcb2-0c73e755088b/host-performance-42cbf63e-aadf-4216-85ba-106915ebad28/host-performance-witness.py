"""Read-only bounded Windows PDH/power witness, never a robot acceptance gate.

Run from Windows Python. No Set* API, registry/power/priority/affinity writes,
process signals, administrator fallback, or collection of other process text.
The Linux lease owner retains exclusive cleanup and service restoration.
"""
import argparse
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid


class Power(c.Structure):
    _fields_ = [('ac',w.BYTE),('battery_flag',w.BYTE),('battery_percent',w.BYTE),
                ('system_status',w.BYTE),('life_s',w.DWORD),('full_life_s',w.DWORD)]


class ValueUnion(c.Union):
    _fields_ = [('double',c.c_double),('large',c.c_longlong)]


class CounterValue(c.Structure):
    _fields_ = [('status',w.DWORD),('value',ValueUnion)]


class Entry(c.Structure):
    _fields_ = [('size',w.DWORD),('usage',w.DWORD),('pid',w.DWORD),
                ('heap',c.c_size_t),('module',w.DWORD),('threads',w.DWORD),
                ('parent',w.DWORD),('priority',w.LONG),('flags',w.DWORD),
                ('exe',w.WCHAR*260)]


class Throttle(c.Structure):
    _fields_ = [('version',w.DWORD),('control',w.DWORD),('state',w.DWORD)]


class HostWitness:
    def __init__(self):
        self.k = c.WinDLL('kernel32',use_last_error=True)
        self.p = c.WinDLL('pdh',use_last_error=True)
        self.k.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD]
        self.k.CreateToolhelp32Snapshot.restype=w.HANDLE
        self.k.Process32FirstW.argtypes=[w.HANDLE,c.POINTER(Entry)]
        self.k.Process32NextW.argtypes=[w.HANDLE,c.POINTER(Entry)]
        self.k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]
        self.k.OpenProcess.restype=w.HANDLE
        self.k.CloseHandle.argtypes=[w.HANDLE]
        self.k.GetProcessInformation.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD]
        self.p.PdhOpenQueryW.argtypes=[w.LPCWSTR,c.c_size_t,c.POINTER(w.HANDLE)]
        self.p.PdhAddEnglishCounterW.argtypes=[w.HANDLE,w.LPCWSTR,c.c_size_t,c.POINTER(w.HANDLE)]
        self.p.PdhCollectQueryData.argtypes=[w.HANDLE]
        self.p.PdhGetFormattedCounterValue.argtypes=[w.HANDLE,w.DWORD,c.c_void_p,c.POINTER(CounterValue)]
        self.p.PdhCloseQuery.argtypes=[w.HANDLE]
        self.query=w.HANDLE()
        if self.p.PdhOpenQueryW(None,0,c.byref(self.query)):
            raise RuntimeError('PDH open failed; no elevated fallback')
        self.counters={}
        for key,suffix in [('performance_percent','% Processor Performance'),
                           ('frequency_mhz','Processor Frequency'),
                           ('utility_percent','% Processor Utility')]:
            counter=w.HANDLE()
            status=self.p.PdhAddEnglishCounterW(self.query,
                '\\Processor Information(_Total)\\'+suffix,0,c.byref(counter))
            if status:
                self.close()
                raise RuntimeError(f'PDH add {key} failed: {status & 0xffffffff:x}')
            self.counters[key]=counter
        self.p.PdhCollectQueryData(self.query)

    def qos(self):
        snapshot=self.k.CreateToolhelp32Snapshot(2,0)
        if snapshot==c.c_void_p(-1).value:
            return {'enumeration_error':c.get_last_error()}
        output=[]
        try:
            entry=Entry();entry.size=c.sizeof(entry)
            more=self.k.Process32FirstW(snapshot,c.byref(entry))
            while more:
                if entry.exe.lower().startswith('vmmem'):
                    item={'pid':entry.pid,'exe':entry.exe,'base_priority':entry.priority,
                          'thread_count':entry.threads}
                    handle=self.k.OpenProcess(0x1000,False,entry.pid)
                    if not handle:
                        item['query_error']=c.get_last_error()
                    else:
                        try:
                            state=Throttle(1,0,0)
                            if self.k.GetProcessInformation(handle,4,c.byref(state),c.sizeof(state)):
                                item.update(control_mask=state.control,state_mask=state.state,
                                    explicit_ecoqos=bool(state.control & state.state & 1))
                            else:item['query_error']=c.get_last_error()
                        finally:self.k.CloseHandle(handle)
                    output.append(item)
                more=self.k.Process32NextW(snapshot,c.byref(entry))
        finally:self.k.CloseHandle(snapshot)
        return output

    def sample(self,*,qos=False):
        start=time.perf_counter_ns();cpu=time.process_time_ns()
        result={'qpc_ns':start,'utc_ns':time.time_ns()}
        result['collect_status']=self.p.PdhCollectQueryData(self.query)
        for key,counter in self.counters.items():
            value=CounterValue()
            status=self.p.PdhGetFormattedCounterValue(counter,0x200,None,c.byref(value))
            result[key]={'api_status':status,'data_status':value.status,
                         'value':value.value.double if not status and value.status in (0,1) else None}
        power=Power()
        result['power']={n:getattr(power,n) for n,_ in power._fields_} if self.k.GetSystemPowerStatus(c.byref(power)) else {'error':c.get_last_error()}
        if qos:result['vm_process_qos']=self.qos()
        result['observer_cpu_ns']=time.process_time_ns()-cpu
        result['observer_wall_ns']=time.perf_counter_ns()-start
        return result

    def close(self):
        if self.query:
            self.p.PdhCloseQuery(self.query);self.query=w.HANDLE()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    repo=Path.cwd().resolve()
    base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
    target=base/('host-performance-'+str(uuid.uuid4()))
    target.mkdir()
    source=Path(__file__).read_bytes();(target/Path(__file__).name).write_bytes(source)
    witness=HostWitness()
    rows=[];child=None
    result={'scope':'bounded_read_only_host_performance_not_acceptance_or_causality',
            'pid':os.getpid(),'source_sha256':hashlib.sha256(source).hexdigest(),
            'interval_s':2,'max_samples':300,'api_writes':False,
            'references':[
                'https://learn.microsoft.com/en-us/windows/win32/procthread/quality-of-service',
                'https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocessinformation',
                'https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetformattedcountervalue']}
    def save():
        (target/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    try:
        # Toolhelp enumeration costs 8--13ms on this host and access to vmmem
        # QoS is denied (5). Retain one pre-engine observation; never repeat it
        # during physics or infer unobservable EcoQoS state.
        result['pre_engine_qos_snapshot']=witness.sample(qos=True)
        for i in range(10):
            time.sleep(.1);rows.append(witness.sample())
        result['pre_engine_self_samples']=rows.copy()
        result['pre_engine_self_cost']={'samples':len(rows),
            'max_wall_ns':max(r['observer_wall_ns'] for r in rows),
            'max_cpu_ns':max(r['observer_cpu_ns'] for r in rows),
            'mean_cpu_ns':sum(r['observer_cpu_ns'] for r in rows)/len(rows)}
        result['self_cost_gate']=result['pre_engine_self_cost']['max_wall_ns']<=10_000_000 and result['pre_engine_self_cost']['mean_cpu_ns']<2_000_000
        if not result['self_cost_gate']:raise RuntimeError('observer too costly; engine not started')
        rows=[]
        if args.run:
            command=['wsl.exe','-d','Ubuntu-24.04','-u','jinho','--','env','CH13_CONTACT_COMPONENT=1',
                'python3','.superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/temporary-clock-session.py',
                '--service-only','--compensated-tick-read-only','--measured-clock-witness',
                '--single-pair-diagnostic','--engine','gazebo']
            result['command']=command;save()
            with (target/'owned-root-output.log').open('wb') as log:
                child=subprocess.Popen(command,cwd=repo,stdout=log,stderr=subprocess.STDOUT)
                result['owned_wsl_client_pid']=child.pid;save()
                print(json.dumps({'path':str(target),'pid':child.pid,'self_cost':result['pre_engine_self_cost']}),flush=True)
                while child.poll() is None:
                    if len(rows)<300:rows.append(witness.sample())
                    time.sleep(2)
                result['exit_code']=child.returncode
                result['parent_reaped']=True
        else:
            rows=[witness.sample(qos=True)]
        result['samples']=rows
    except BaseException as error:
        result['observer_error']=repr(error)
        # Never kill the lease owner or detach its cleanup on observer errors.
        if child is not None:
            result['exit_code']=child.wait();result['parent_reaped']=True
        raise
    finally:
        result['samples']=rows
        witness.close();result['observer_closed']=True;save()
    print(json.dumps({'path':str(target),'self_cost':result['pre_engine_self_cost'],
                      'samples':len(rows),'exit_code':result.get('exit_code')}),flush=True)


if __name__=='__main__':main()
