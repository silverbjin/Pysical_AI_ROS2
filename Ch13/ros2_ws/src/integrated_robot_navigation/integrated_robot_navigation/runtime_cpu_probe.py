"""Bounded Linux diagnostic reads. No ROS, control, priority or clock writes."""
import os
from pathlib import Path
import time


def clock_sample(*,clock=time):
    before=clock.clock_gettime_ns(clock.CLOCK_MONOTONIC_RAW)
    wall=clock.clock_gettime_ns(clock.CLOCK_MONOTONIC)
    system=clock.time_ns()
    after=clock.clock_gettime_ns(clock.CLOCK_MONOTONIC_RAW)
    if after<before:raise RuntimeError('diagnostic raw clock rollback')
    return dict(raw_before_ns=before,wall_ns=wall,system_ns=system,raw_after_ns=after)


def optional_thread_sample(pid,expected_pgid,expected_start,*,enabled=False):
    """Broad procfs walks are diagnostic opt-in, never a required witness.

    Actual WSL collection consumed up to20ms CPU/72ms elapsed per scan. Keep
    cheap RAW brackets and original process totals without this perturbation.
    """
    if not enabled:return None
    return sample_owned_threads(pid,expected_pgid,expected_start)


def _identity(path,expected_pgid,expected_start):
    text=(path/'stat').read_text();fields=text.rsplit(')',1)[1].split()
    if fields[0] in ('Z','X','x'):raise ProcessLookupError('diagnostic process exited')
    if (int(fields[2]),int(fields[19]))!=(expected_pgid,expected_start):
        raise RuntimeError('diagnostic process identity changed')
    if (path/'stat').stat().st_uid!=os.getuid():
        # procfs may change stat's file owner while this same process exits.
        # Confirm its original identity AND terminal state; never accept a live
        # foreign or recycled process as an ordinary exit.
        terminal=(path/'stat').read_text().rsplit(')',1)[1].split()
        if ((int(terminal[2]),int(terminal[19]))==(expected_pgid,expected_start)
                and terminal[0] in ('Z','X','x')):
            raise ProcessLookupError('diagnostic process exited')
        raise RuntimeError('diagnostic process identity changed')


def sample_owned_threads(pid,expected_pgid,expected_start,*,proc_root=Path('/proc'),max_threads=96):
    if type(max_threads) is not int or not 1<=max_threads<=128:
        raise ValueError('bounded thread sample required')
    path=Path(proc_root)/str(pid);_identity(path,expected_pgid,expected_start)
    wall=time.monotonic_ns();raw=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
    cpu=time.thread_time_ns();ids=[]
    for entry in (path/'task').iterdir():
        if entry.name.isdecimal():ids.append(int(entry.name))
        if len(ids)>max_threads:break
    truncated=len(ids)>max_threads;rows=[];missing=0
    for tid in sorted(ids)[:max_threads]:
        root=path/'task'/str(tid)
        try:
            text=(root/'stat').read_text();fields=text.rsplit(')',1)[1].split()
            if fields[0] in ('Z','X','x'):raise ProcessLookupError('thread exited')
            counters=tuple(map(int,(root/'schedstat').read_text().split()))
            if len(counters)!=3 or min(counters)<0:raise ValueError('invalid thread scheduler counters')
            rows.append(dict(tid=tid,name=text[text.index('(')+1:text.rindex(')')],
                start_ticks=int(fields[19]),runtime_ns=counters[0],runqueue_wait_ns=counters[1],timeslices=counters[2]))
        except (OSError,ValueError,IndexError):missing+=1
    _identity(path,expected_pgid,expected_start)
    cpu_ns=time.thread_time_ns()-cpu
    raw_ns=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)-raw
    wall_ns=time.monotonic_ns()-wall
    return dict(scope='owned_thread_diagnostic_not_control_or_physics_cpu',read_only=True,
        max_threads=max_threads,truncated=truncated,unavailable_threads=missing,threads=rows,
        collection_wall_ns=wall_ns,collection_raw_ns=raw_ns,collection_thread_ns=cpu_ns)
