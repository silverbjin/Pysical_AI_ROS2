"""Bounded read-only timing/owned-thread evidence, never a control input."""
import importlib,importlib.util,os
from pathlib import Path
from types import SimpleNamespace
import pytest


def api():
    name='integrated_robot_navigation.runtime_cpu_probe'
    assert importlib.util.find_spec(name),'runtime clock/scheduler boundary is unobserved'
    return importlib.import_module(name)


def stat(group=50,start=123):
    fields=['0']*22;fields[0]='S';fields[2]=str(group);fields[19]=str(start)
    return '11 (thread name) '+' '.join(fields)


def proc(tmp_path,count=2):
    p=tmp_path/'11';p.mkdir();(p/'stat').write_text(stat());(p/'task').mkdir()
    for i in range(count):
        t=p/'task'/str(11+i);t.mkdir();(t/'stat').write_text(stat(start=123+i))
        (t/'schedstat').write_text('1000 2000 3\n')
    return p


def test_clock_fields_are_bracketed_without_cross_domain_subtraction():
    calls=[];raw=iter((10,40))
    def read(k):
        calls.append(k);return next(raw) if k==4 else 20
    clock=SimpleNamespace(CLOCK_MONOTONIC_RAW=4,CLOCK_MONOTONIC=1,clock_gettime_ns=read,time_ns=lambda:30)
    result=api().clock_sample(clock=clock)
    assert result==dict(raw_before_ns=10,wall_ns=20,system_ns=30,raw_after_ns=40)
    assert calls==[4,1,4]


def test_owned_threads_have_identity_and_separate_runtime_wait_counters(tmp_path):
    proc(tmp_path);result=api().sample_owned_threads(11,50,123,proc_root=tmp_path)
    assert result['read_only'] is True and result['truncated'] is False
    assert len(result['threads'])==2
    assert result['threads'][0]==dict(tid=11,name='thread name',start_ticks=123,
        runtime_ns=1000,runqueue_wait_ns=2000,timeslices=3)
    # These clocks may have different rates under clock discipline / WSL.
    # A diagnostic must retain the anomaly, not reject or clamp its evidence.
    assert all(type(result[k]) is int and result[k]>=0 for k in
        ('collection_wall_ns','collection_raw_ns','collection_thread_ns'))


@pytest.mark.parametrize('bad',['group','identity'])
def test_foreign_or_replaced_process_is_not_sampled(tmp_path,bad):
    p=proc(tmp_path);(p/'stat').write_text(stat(group=51 if bad=='group' else 50,start=124 if bad=='identity' else 123))
    with pytest.raises(RuntimeError,match='identity'):api().sample_owned_threads(11,50,123,proc_root=tmp_path)


def test_thread_cap_and_racing_exit_are_explicit_not_silently_complete(tmp_path):
    p=proc(tmp_path,5);(p/'task'/'11'/'schedstat').unlink()
    r=api().sample_owned_threads(11,50,123,proc_root=tmp_path,max_threads=3)
    assert r['truncated'] is True and len(r['threads'])<=3
    # A bounded directory scan deliberately makes no promise about which TIDs
    # fall in a truncated subset. Check the exit race in an untruncated scan.
    full=api().sample_owned_threads(11,50,123,proc_root=tmp_path,max_threads=8)
    assert full['truncated'] is False and full['unavailable_threads']==1
    assert len(full['threads'])==4


def test_actual_self_read_never_changes_process_resources():
    before=(os.getpid(),os.getpgrp(),os.getuid(),os.sched_getaffinity(0))
    start=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19])
    r=api().sample_owned_threads(before[0],before[1],start)
    assert r['threads'] and r['read_only'] is True
    assert before==(os.getpid(),os.getpgrp(),os.getuid(),os.sched_getaffinity(0))


def test_expensive_thread_walk_is_opt_in_and_disabled_does_no_io(monkeypatch):
    module=api();calls=[]
    monkeypatch.setattr(module,'sample_owned_threads',lambda *args,**kw:calls.append(args) or {'read_only':True})
    assert module.optional_thread_sample(11,50,123) is None
    assert calls==[]
    assert module.optional_thread_sample(11,50,123,enabled=True)=={'read_only':True}
    assert calls==[(11,50,123)]


@pytest.mark.parametrize('terminal',[True,False])
def test_exit_owner_race_is_distinguished_from_a_foreign_live_process(tmp_path,monkeypatch,terminal):
    p=proc(tmp_path);original_read=Path.read_text;original_stat=Path.stat;calls=[0]
    def read(path,*a,**kw):
        if path==p/'stat':
            calls[0]+=1
            text=stat()
            return text.replace(' S ',' Z ') if terminal and calls[0]>1 else text
        return original_read(path,*a,**kw)
    def owner(path,*a,**kw):
        if path==p/'stat':return SimpleNamespace(st_uid=os.getuid()+1)
        return original_stat(path,*a,**kw)
    monkeypatch.setattr(Path,'read_text',read);monkeypatch.setattr(Path,'stat',owner)
    expected=ProcessLookupError if terminal else RuntimeError
    with pytest.raises(expected):api().sample_owned_threads(11,50,123,proc_root=tmp_path)
