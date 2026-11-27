"""R09: compare elapsed rates using Windows QPC-bounded WSL RPCs.
QPC is independent of guest time discipline, not an external UTC standard.
"""
import argparse
from bisect import bisect_left, bisect_right
import json
import subprocess
import time
from pathlib import Path
from clock_drift_analyzer import analyze


def read_jsonl(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s]


def choose(anchors, phase):
    eligible = [a for a in anchors if a.get('phase') == phase and a.get('guest') and
                0 <= a['qpc_after_ns']-a['qpc_before_ns'] <= 500_000_000]
    return min(eligible, key=lambda a:a['qpc_after_ns']-a['qpc_before_ns']) if eligible else None


def bounds(before, after, value):
    lo = after['qpc_before_ns']-before['qpc_after_ns']
    hi = after['qpc_after_ns']-before['qpc_before_ns']
    elapsed = value(after['guest'])-value(before['guest'])
    if lo <= 0 or elapsed <= 0:
        return None
    return {'elapsed_guest_s':elapsed/1e9,'elapsed_qpc_lower_s':lo/1e9,'elapsed_qpc_upper_s':hi/1e9,
            'lower_ppm':(elapsed/hi-1)*1e6,'upper_ppm':(elapsed/lo-1)*1e6}


def matched_bounds(anchors, host_rows, key):
    """Bound same-kind elapsed rates with host samples bracketing Docker RPCs."""
    if key == 'monotonic':
        reads=[(r['monotonic_ns'],r['monotonic_ns'],r['monotonic_ns']) for r in host_rows]
    else:
        reads=[(d['m0'],d['m1'],d['value_ns']) for r in host_rows if (d:=r['reads'].get(key)) is not None]
    starts=[r[0] for r in reads]; ends=[r[1] for r in reads]
    if starts!=sorted(starts) or ends!=sorted(ends): return None
    def candidates(phase):
        out=[]
        for a in anchors:
            if a.get('phase')!=phase or not a.get('guest'): continue
            q0,q1=a['qpc_before_ns'],a['qpc_after_ns']
            if not 0<=q1-q0<=500_000_000: continue
            i=bisect_right(ends,q0)-1; j=bisect_left(starts,q1)
            if i<0 or j>=len(reads) or i>=j or reads[j][1]-reads[i][0]>1_000_000_000: continue
            local=reads[i:j+1]
            if any(not 0<=x[1]-x[0]<=5_000_000 for x in local): continue
            if any(b[0]-a[1]>250_000_000 or b[2]<a[2] or (key=='realtime' and abs((b[2]-a[2])-(b[0]-a[0]))>100_000_000) for a,b in zip(local,local[1:])): continue
            try:
                g=a['guest']['monotonic_ns'] if key=='monotonic' else a['guest']['reads'][key]['value_ns']
            except KeyError: continue
            out.append((local[0][2],local[-1][2],g,q0,q1))
        return out
    before,after=candidates('before'),candidates('after')
    if not before or not after:return None
    a=min(before,key=lambda x:x[1]-x[0]); b=min(after,key=lambda x:x[1]-x[0])
    lo,hi=b[0]-a[1],b[1]-a[0]; elapsed=b[2]-a[2]; coverage=b[3]-a[4]
    if lo<=0 or elapsed<=0 or coverage<=0:return None
    return dict(reference_clock=key,elapsed_guest_s=elapsed/1e9,elapsed_reference_lower_s=lo/1e9,elapsed_reference_upper_s=hi/1e9,coverage_monotonic_lower_s=coverage/1e9,lower_ppm=(elapsed/hi-1)*1e6,upper_ppm=(elapsed/lo-1)*1e6)


def docker_anchors(path, name, label, seconds):
    # Capture response after a container has started; use at most 500ms RPCs.
    end=time.monotonic()+seconds
    f=path/(label+'-anchors.jsonl')
    code='import json,sys;sys.path.insert(0,"/diag");from clock_diag import sample;print(json.dumps(sample(scope="container_idle")))'
    with f.open('x',buffering=1) as out:
        for phase, target in [('before',time.monotonic()),('after',end-5)]:
            time.sleep(max(0,target-time.monotonic()))
            for _ in range(5):
                q0=time.monotonic_ns(); guest=None; error=None
                try:
                    p=subprocess.run(['docker','exec',name,'python3','-c',code],capture_output=True,text=True,timeout=1,check=True)
                    guest=json.loads(p.stdout)
                except (subprocess.SubprocessError,ValueError,OSError) as e:
                    error=type(e).__name__
                q1=time.monotonic_ns()
                out.write(json.dumps(dict(phase=phase,qpc_before_ns=q0,qpc_after_ns=q1,guest=guest,error=error))+'\n')
                time.sleep(.1)
    rows=read_jsonl(f)
    return 0 if choose(rows,'before') and choose(rows,'after') else 1


def analyze_phase(path):
    output={'status':'REVIEW_REQUIRED','layers':{},'guest_vs_qpc':{},'origin':'UNKNOWN'}
    for name in ('windows','host','container','container_ros'):
        file = path/'windows.jsonl' if name=='windows' else path/name/'samples.jsonl'
        if not file.is_file():
            output['layers'][name]={'quality':'NOT_AVAILABLE'}
            continue
        try:
            output['layers'][name]=analyze(read_jsonl(file))
        except (ValueError,KeyError,OSError) as e:
            output['layers'][name]={'quality':'PARTIAL','error':str(e)}
    try:
        anchors=read_jsonl(path/'anchors.jsonl')
        a,b=choose(anchors,'before'),choose(anchors,'after')
        if a is None or b is None:
            raise ValueError('no valid bounded anchors')
        output['anchor_rtt_ns']=[v['qpc_after_ns']-v['qpc_before_ns'] for v in (a,b)]
        for key in ('monotonic','monotonic_raw','realtime','boottime'):
            value=(lambda r:r['monotonic_ns']) if key=='monotonic' else (lambda r,k=key:r['reads'][k]['value_ns'])
            try:
                output['guest_vs_qpc'][key]=bounds(a,b,value)
            except KeyError:
                output['guest_vs_qpc'][key]=None
    except (ValueError,KeyError,OSError) as e:
        output['anchor_error']=str(e)
    output['container_vs_host']={}
    for name in ('container','container_ros'):
        try:
            anchors=read_jsonl(path/(name+'-anchors.jsonl'))
            a,b=choose(anchors,'before'),choose(anchors,'after')
            if not a or not b: raise ValueError('no valid Docker RPC brackets')
            host_rows=read_jsonl(path/'host'/'samples.jsonl')
            output['container_vs_host'][name] = {k:matched_bounds(anchors,host_rows,k) for k in ('monotonic','realtime','monotonic_raw')}
        except (ValueError,KeyError,OSError) as e:
            output['container_vs_host'][name]={'quality':'NOT_AVAILABLE','error':str(e)}
    output['provisional_gate']=gate(output,path)
    return output


def gate(output,path):
    # Proposed diagnostic threshold only; not a robot freshness/control contract.
    limit=1000
    phase=path.name
    required={'windows':['realtime'],'host':['realtime','monotonic_raw','boottime']}
    if phase=='docker':
        required.update(container=['realtime','monotonic_raw','boottime'],container_ros=['realtime','monotonic_raw','boottime','system_time','steady_time','ros_time'])
    failures=[];unknown=[]
    def check_rate(label,r):
        if not r: unknown.append(label+': no rate');return
        lo,hi=r['lower_ppm'],r['upper_ppm']
        if lo>limit or hi< -limit: failures.append(label+': rate outside')
        elif lo< -limit or hi>limit: unknown.append(label+': rate uncertainty')
    for layer,keys in required.items():
        data=output['layers'].get(layer,{})
        if data.get('quality')!='COMPLETE' or data.get('duration_s',0)<600: unknown.append(layer+': coverage')
        for key in keys:
            d=data.get('clocks',{}).get(key,{})
            if not d or d.get('quality')!='COMPLETE': unknown.append(layer+'/'+key+': quality')
            if any(e['kind'] in ('FORWARD','BACKWARD') for e in d.get('events',[])): failures.append(layer+'/'+key+': step')
            check_rate(layer+'/'+key+'/total',d.get('total_rate'))
            for i,r in enumerate(d.get('windows',[])): check_rate(layer+'/'+key+'/window'+str(i),r)
    for key in ('monotonic','monotonic_raw','realtime','boottime'):
        r=output['guest_vs_qpc'].get(key)
        if not r or r['elapsed_qpc_lower_s']<600: unknown.append('guest_vs_qpc/'+key+': coverage')
        check_rate('guest_vs_qpc/'+key,r)
    if phase=='docker':
        for layer in ('container','container_ros'):
            for key in ('monotonic','monotonic_raw','realtime'):
                r=output['container_vs_host'].get(layer,{}).get(key)
                if not r or r['coverage_monotonic_lower_s']<600: unknown.append(layer+'/host/'+key+': coverage')
                check_rate(layer+'/host/'+key,r)
    if not (path/'timex-samples.jsonl').is_file(): unknown.append('timex: unavailable')
    return {'result':'DIAGNOSTIC_FAIL' if failures else 'INCONCLUSIVE' if unknown else 'CANDIDATE_WITHIN_REVIEW_REQUIRED',
            'rate_limit_ppm_provisional':limit,'min_s':600,'failures':failures,'unknown':unknown,'not_owner_acceptance':True}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',type=Path)
    p.add_argument('--docker-anchor');p.add_argument('--label',choices=('container','container_ros'));p.add_argument('--seconds',type=int);a=p.parse_args()
    if a.docker_anchor:
        if not a.label or not a.seconds or a.seconds<20: p.error('Docker anchor requires label and at least 20 seconds')
        raise SystemExit(docker_anchors(a.phase,a.docker_anchor,a.label,a.seconds))
    print(json.dumps(analyze_phase(a.phase),indent=2))
