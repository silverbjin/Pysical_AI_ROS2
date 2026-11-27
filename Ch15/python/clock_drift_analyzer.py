"""Read-only R08 analysis of bracketed clock_diag.py JSONL. No time changes.
All rates are relative to MONOTONIC, not proof of absolute clock accuracy.
"""
import argparse
import json
import statistics
from pathlib import Path

NS = 10**9
STEP = 100_000_000
BRACKET = 5_000_000
GAP = 250_000_000
WINDOW = 10*NS


def offset(r):
    return r['value_ns']-r['m1'], r['value_ns']-r['m0']


def valid(r):
    return r is not None and 0 <= r['m1']-r['m0'] <= BRACKET


def delta(a, b):
    al, ah = offset(a)
    bl, bh = offset(b)
    return bl-ah, bh-al


def rate(a, b):
    lo, hi = delta(a, b)
    # Unknown read times: conservative elapsed bounds, not a point estimate.
    dtlo, dthi = b['m0']-a['m1'], b['m1']-a['m0']
    if dtlo <= 0:
        return None
    bounds = [x/t*1e6 for x in (lo,hi) for t in (dtlo,dthi)]
    return dict(lower_ppm=min(bounds), upper_ppm=max(bounds),
                midpoint_ppm=(min(bounds)+max(bounds))/2, start_ns=a['m0'], end_ns=b['m1'])


def analyze(rows):
    if not rows:
        return {'quality':'INSUFFICIENT','clocks':{},'origin':'UNKNOWN'}
    if len({r['scope'] for r in rows}) != 1 or any(b['monotonic_ns'] <= a['monotonic_ns'] for a,b in zip(rows,rows[1:])):
        raise ValueError('mixed scope or non-increasing MONOTONIC')
    keys = sorted({k for r in rows for k in r['reads']})
    result = {}
    for k in keys:
        events, windows, segment, gaps = [], [], [], 0
        first = last = None
        for row in rows:
            r = row['reads'].get(k)
            if not valid(r) or (k == 'ros_time' and row.get('sim_time') is not False):
                gaps += 1
                segment = []
                continue
            if first is None:
                first = r
            last = r
            if segment:
                p = segment[-1]
                lo,hi = delta(p,r)
                gap = r['m0']-p['m1']
                if gap < 0 or gap > GAP:
                    gaps += 1
                    events.append(dict(kind='COVERAGE_GAP',at_ns=r['m1'],lower_ns=lo,upper_ns=hi))
                    segment = []
                elif lo > STEP or hi < -STEP:
                    events.append(dict(kind='FORWARD' if lo > STEP else 'BACKWARD',at_ns=r['m1'],lower_ns=lo,upper_ns=hi))
                    segment = []
                elif lo < -STEP or hi > STEP:
                    gaps += 1
                    segment = []
            segment.append(r)
            if r['m0']-segment[0]['m1'] >= WINDOW:
                windows.append(rate(segment[0],r))
                segment = [r]
        steps = [e for e in events if e['kind'] in ('FORWARD','BACKWARD')]
        intervals = [(b['at_ns']-a['at_ns'])/NS for a,b in zip(steps,steps[1:]) if a['kind']==b['kind']]
        total = rate(first,last) if first is not None and last is not None and last['m0']-first['m1']>=WINDOW else None
        result[k] = dict(total_rate=total, offset_change_ns=delta(first,last) if first and last else None,
                         windows=windows, median_clean_ppm=statistics.median(w['midpoint_ppm'] for w in windows) if windows else None,
                         events=events, gaps=gaps, same_direction_intervals_s=intervals,
                         quality='PARTIAL' if gaps else 'COMPLETE' if windows else 'INSUFFICIENT')
    # The accumulated RAW offset over each successive REALTIME forward step interval.
    rt = result.get('realtime',{})
    raw = result.get('monotonic_raw',{})
    paired = []
    steps = [e for e in rt.get('events',[]) if e['kind'] in ('FORWARD','BACKWARD')]
    # Pair each step with RAW offset change over the same local interval;
    # do not use a run-wide median across a regime transition.
    raw_reads = [(r['reads']['realtime']['m1'],r['reads']['monotonic_raw'])
                 for r in rows if valid(r['reads'].get('realtime')) and valid(r['reads'].get('monotonic_raw'))]
    import bisect
    times=[t for t,_ in raw_reads]
    for a,b in zip(steps,steps[1:]):
        if a['kind'] != 'FORWARD' or b['kind'] != 'FORWARD':
            continue
        i,j=bisect.bisect_left(times,a['at_ns']),bisect.bisect_left(times,b['at_ns'])
        if i>=len(times) or j>=len(times) or times[i]!=a['at_ns'] or times[j]!=b['at_ns']:
            continue
        if any(a['at_ns'] < e['at_ns'] <= b['at_ns'] for e in raw.get('events',[])) or raw.get('gaps'):
            continue
        lo,hi=delta(raw_reads[i][1],raw_reads[j][1])
        observed=(b['lower_ns']+b['upper_ns'])/(2*NS)
        predicted=(lo+hi)/(2*NS)
        paired.append(dict(interval_s=(b['at_ns']-a['at_ns'])/NS, predicted_s=predicted,
                           predicted_bounds_s=[lo/NS,hi/NS], observed_s=observed, residual_s=observed-predicted))
    return dict(scope=rows[0]['scope'], samples=len(rows), duration_s=(rows[-1]['monotonic_ns']-rows[0]['monotonic_ns'])/NS,
                quality='COMPLETE' if result and all(v['quality']=='COMPLETE' for v in result.values()) else 'PARTIAL',
                clocks=result, forward_pairs=paired, origin='UNKNOWN')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('samples',type=Path)
    a=p.parse_args()
    print(json.dumps(analyze([json.loads(s) for s in a.samples.read_text().splitlines() if s]),indent=2))


if __name__=='__main__':
    main()
