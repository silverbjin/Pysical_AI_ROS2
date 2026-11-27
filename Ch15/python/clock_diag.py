"""Read-only clock diagnosis. No settime, /clock publication or safety override.

For a clock read at an unknown instant in [m0,m1], its difference from
MONOTONIC is in [value-m1, value-m0]. Consecutive intervals bound the
offset change even when a process is descheduled around a clock read.
"""
import argparse,json,signal,sys,time
from pathlib import Path

STEP_NS=100_000_000   # diagnostic threshold, NOT a control threshold
MAX_BRACKET_NS=5_000_000
MAX_GAP_NS=250_000_000
PERIOD_NS=50_000_000
def bracket(fn):
    a=time.monotonic_ns();v=int(fn());b=time.monotonic_ns()
    return dict(m0=a,m1=b,value_ns=v)
def sample(clocks=None,scope='host',sim_time=None):
    reads={'realtime':bracket(time.time_ns)}
    for name,key in [('boottime','CLOCK_BOOTTIME'),('monotonic_raw','CLOCK_MONOTONIC_RAW')]:
        if hasattr(time,key):reads[name]=bracket(lambda k=getattr(time,key):time.clock_gettime_ns(k))
    for key,fn in (clocks or {}).items():reads[key]=bracket(fn)
    return dict(scope=scope,sim_time=sim_time,monotonic_ns=time.monotonic_ns(),reads=reads)
def interval(r):
    return r['value_ns']-r['m1'],r['value_ns']-r['m0']
def compare(a,b,key):
    x=a['reads'].get(key);y=b['reads'].get(key)
    if x is None or y is None:return dict(kind='UNAVAILABLE')
    gap=y['m0']-x['m1']
    if any(r['m1']<r['m0'] or r['m1']-r['m0']>MAX_BRACKET_NS for r in (x,y)) or gap<0:
        return dict(kind='AMBIGUOUS_BRACKET',gap_ns=gap)
    lo0,hi0=interval(x);lo1,hi1=interval(y)
    lo=lo1-hi0;hi=hi1-lo0
    kind='FORWARD' if lo>STEP_NS else 'BACKWARD' if hi< -STEP_NS else 'STABLE_INTERVAL' if lo>=-STEP_NS and hi<=STEP_NS else 'AMBIGUOUS_THRESHOLD'
    return dict(kind=kind,offset_change_lower_ns=lo,offset_change_upper_ns=hi,gap_ns=gap,window_start_ns=x['m0'],window_end_ns=y['m1'],coverage_gap=gap>MAX_GAP_NS)
def summarize(rows):
    keys=sorted({k for row in rows for k in row['reads']})
    counts={k:{} for k in keys};events=[];gaps=0
    for a,b in zip(rows,rows[1:]):
        if a['scope']!=b['scope']:raise ValueError('mixed scopes')
        if b['monotonic_ns']<=a['monotonic_ns']:raise ValueError('monotonic order invalid')
        if b['monotonic_ns']-a['monotonic_ns']>MAX_GAP_NS:gaps+=1
        for key in keys:
            d=compare(a,b,key);kind=d['kind']
            # A simulated ROS clock is not expected to track system time.
            if key=='ros_time' and (a['sim_time'] is not False or b['sim_time'] is not False):
                kind='SIM_OR_UNKNOWN_ROS_CLOCK';d['kind']=kind
            counts[key][kind]=counts[key].get(kind,0)+1
            if kind not in ('STABLE_INTERVAL','SIM_OR_UNKNOWN_ROS_CLOCK'):
                events.append(dict(clock=key,**d))
    steps=[e for e in events if e['clock'] in ('realtime','system_time','ros_time') and e['kind'] in ('FORWARD','BACKWARD')]
    quality='INSUFFICIENT' if len(rows)<2 else 'PARTIAL' if gaps or any(e['kind'].startswith('AMBIGUOUS') or e['kind']=='UNAVAILABLE' for e in events) else 'COMPLETE'
    return dict(schema=1,scope=rows[0]['scope'] if rows else None,samples=len(rows),quality=quality,threshold_ns=STEP_NS,max_bracket_ns=MAX_BRACKET_NS,max_gap_ns=MAX_GAP_NS,sampling_gaps=gaps,counts=counts,events=events,observed_system_or_ros_step=bool(steps),result='DISCONTINUITY_OBSERVED' if steps else 'NO_STEP_OBSERVED_IN_SAMPLES' if quality=='COMPLETE' else 'INCONCLUSIVE',origin='NOT_INFERRED')
def read_rows(path):
    return [json.loads(s) for s in Path(path).read_text().splitlines() if s]
def write_summary(path,rows):
    data=summarize(rows);Path(path).write_text(json.dumps(data,indent=2)+'\n');return data
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--duration',type=float,required=True)
    p.add_argument('--ros',action='store_true')
    p.add_argument('--scope',choices=('wsl_host','container_idle'),required=True)
    a=p.parse_args()
    if not 0<a.duration<=1300:raise ValueError('duration range')
    stop=False
    def handler(sig,frame):
        nonlocal stop
        stop=True
    for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,handler)
    clocks={};node=None;initialized=False;sim=None
    try:
        if a.ros:
            import rclpy
            from rclpy.node import Node
            from rclpy.clock import Clock,ClockType
            from rclpy.signals import SignalHandlerOptions
            rclpy.init(signal_handler_options=SignalHandlerOptions.NO);initialized=True
            node=Node('g09_idle_clock_diag')
            sys_clock=Clock(clock_type=ClockType.SYSTEM_TIME);steady=Clock(clock_type=ClockType.STEADY_TIME)
            sim=bool(node.get_parameter('use_sim_time').value)
            clocks={'system_time':lambda:sys_clock.now().nanoseconds,'steady_time':lambda:steady.now().nanoseconds,'ros_time':lambda:node.get_clock().now().nanoseconds}
        a.out.mkdir(parents=True,exist_ok=False)
        end=time.monotonic_ns()+int(a.duration*1e9);deadline=time.monotonic_ns()
        with (a.out/'samples.jsonl').open('x',buffering=1) as f:
            while not stop and time.monotonic_ns()<end:
                f.write(json.dumps(sample(clocks,a.scope,sim),separators=(',',':'))+'\n')
                deadline+=PERIOD_NS
                now=time.monotonic_ns()
                if deadline<now:deadline=now+PERIOD_NS
                time.sleep(max(0,deadline-now)/1e9)
        result=write_summary(a.out/'summary.json',read_rows(a.out/'samples.jsonl'))
        print(json.dumps({k:v for k,v in result.items() if k!='events'}),flush=True)
        return 0 if result['samples']>=2 else 1
    finally:
        if node is not None:node.destroy_node()
        if initialized:rclpy.try_shutdown()
if __name__=='__main__':sys.exit(main())
