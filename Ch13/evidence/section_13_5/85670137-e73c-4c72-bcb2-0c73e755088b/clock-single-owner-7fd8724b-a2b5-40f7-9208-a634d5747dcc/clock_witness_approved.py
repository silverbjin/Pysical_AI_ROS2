"""Read-only continuous original-clock witness, explicit opt-in admission only.

RAW brackets bound the rate uncertainty; no clock/header is rewritten. Kernel
tick/frequency metadata is retained by the caller's unchanged legacy assessor.
This function is not an engine, sensor, controller or ownership success proof.
"""
from collections import deque


def assess_measured_clock_witness(records):
    result=dict(passed=False,scope='continuous_original_clock_witness_not_engine_acceptance',
        declared_duration_ns=150_000_000_000,window_min_ns=1_000_000_000,
        rate_limits=[.999,1.001],maximum_gap_ns=2_000_000_000,history_capacity=512,
        samples=0,windows=0,maximum_history_samples=0,
        minimum_lower_ratio=None,maximum_upper_ratio=None,maximum_call_span_ns=0)
    def integer(value):return type(value) is int and value>=0
    try:
        stream=iter(records);meta=next(stream)
        if (meta.get('kind')!='metadata' or meta.get('adjtimex_modes')!=0
                or meta.get('writes_system_settings') is not False
                or meta.get('raw_duration_ns')!=150_000_000_000):
            raise ValueError('original150s read-only metadata missing or changed')
        history=deque();previous=first=last=None;finished=None
        for row in stream:
            if finished is not None:raise ValueError('record after recorder closure')
            if row.get('kind')=='finished':
                elapsed=row.get('raw_elapsed_ns')
                if (not integer(elapsed) or elapsed<150_000_000_000
                        or row.get('writes_system_settings') is not False):
                    raise ValueError('original150s recording unfinished')
                finished=elapsed;continue
            keys=('raw_before_ns','raw_after_ns','monotonic_ns','realtime_ns','modes','errno','tick_us')
            if (any(not integer(row.get(k)) for k in keys)
                    or type(row.get('freq_scaled_ppm')) is not int
                    or type(row.get('state')) is not int or row['state']<0
                    or row['modes']!=0 or row['errno']!=0
                    or row['tick_us'] not in (9999,10000,10001)):
                raise ValueError('invalid original observation/unsupported encoding/write')
            before,after,mono,real=(row[k] for k in keys[:4])
            if after<before:raise ValueError('RAW query bracket rollback')
            result['maximum_call_span_ns']=max(result['maximum_call_span_ns'],after-before)
            if previous is not None:
                pb,pa,pm,pr=previous
                if before<=pa or mono<=pm or real<=pr:raise ValueError('original clock rollback')
                if before-pa>2_000_000_000:raise ValueError('original observation gap')
                if abs((real-mono)-(pr-pm))>1_000_000:raise ValueError('REALTIME step exceeds original1ms')
            current=(before,after,mono,real)
            if first is None:first=current
            previous=last=current;history.append(current);result['samples']+=1
            while len(history)>1 and before-history[1][1]>=1_000_000_000:history.popleft()
            if len(history)>512:raise ValueError('bounded witness history overflow')
            result['maximum_history_samples']=max(result['maximum_history_samples'],len(history))
            anchor=history[0]
            if before-anchor[1]>=1_000_000_000:
                delta=mono-anchor[2]
                low=delta/(after-anchor[0]);high=delta/(before-anchor[1])
                result['windows']+=1
                old=result['minimum_lower_ratio'];result['minimum_lower_ratio']=low if old is None else min(old,low)
                old=result['maximum_upper_ratio'];result['maximum_upper_ratio']=high if old is None else max(old,high)
                if not .999<=low<=high<=1.001:raise ValueError('actual rate/uncertainty exceeds original0.1percent')
        if finished is None or first is None or not result['windows']:
            raise ValueError('recorder closure/continuous rate evidence missing')
        span=last[1]-first[0]
        # Same150s collector and its final marker; require coverage to its end,
        # within the existing2s observation-gap bound. No longer capture is run.
        if (span<149_000_000_000 or not 0<=finished-span<=2_000_000_000
                or span>152_000_000_000):
            raise ValueError('original150s coverage incomplete or inconsistent')
        result.update(passed=True,observed_span_ns=span,recorder_elapsed_ns=finished,
            recorder_closed=True,writes_system_settings=False)
    except (KeyError,TypeError,ValueError,StopIteration,ZeroDivisionError) as error:
        result['error']=str(error) or 'empty witness'
    return result
