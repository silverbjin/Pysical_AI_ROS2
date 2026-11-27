"""R04: classify evidence, never override the owner/profile verdict."""
import argparse,json,sys,tarfile
from pathlib import Path

THRESHOLD_NS=100_000_000

def classify(owner,record,source,watchdog,events,diagnostic=None):
    result=dict(mode=record.get('mode'),terminal=record.get('terminal'),owner_verdict=owner.get('result'),record_verdict=record.get('result'),classification='FAILURE_UNRESOLVED',clock_origin='UNKNOWN',automatic_retry=False,safety_override=False)
    if record.get('result')=='PASS':
        result['classification']='RECORD_PASS' if owner.get('result')=='PASS' else 'RECORD_PASS_PROFILE_NOT_ACCEPTED'
        return result
    if not all(isinstance(x,list) and x for x in (source,watchdog,events)):
        result['classification']='INSUFFICIENT_EVIDENCE';return result
    if record.get('mode')!='F03_transient' or record.get('terminal')!='ABORTED':return result
    latches=[x for x in watchdog if x.get('kind')=='watchdog' and x.get('first_latch') is True]
    faults=[x for x in events if x.get('event')=='FAULT' and x.get('detail',{}).get('reason')=='readiness_or_safety_lost']
    ends=[x for x in events if x.get('event')=='END' and x.get('detail',{}).get('state')=='ABORTED' and x.get('detail',{}).get('all_terminal') is True]
    if len(latches)!=1 or len(faults)!=1 or len(ends)!=1:return result
    latch=latches[0];fault=faults[0];t=latch['wall_ns'];age=latch.get('age_s')
    if type(age) not in (float,int) or not 0<=age<=.2 or not 0<=fault['steady_ns']-t<=250_000_000:return result
    pubs=[x for x in source if x.get('kind')=='publish_enter']
    scans=[x for x in watchdog if x.get('kind')=='scan' and x['wall_ns']<=t]
    before=[x for x in pubs if x['wall_ns']<=t];after=[x for x in pubs if x['wall_ns']>t]
    prior_events=[x for x in events if x['steady_ns']<fault['steady_ns']]
    if not all((scans,before,after,prior_events)):return result
    a=max(before,key=lambda x:x['wall_ns']);b=min(after,key=lambda x:x['wall_ns']);s=max(scans,key=lambda x:x['wall_ns']);p=max(prior_events,key=lambda x:x['steady_ns'])
    gap=b['wall_ns']-a['wall_ns'];stamp_delta=b['stamp_ns']-a['stamp_ns'];excess=stamp_delta-gap
    mission_excess=(fault['ros_ns']-p['ros_ns'])-(fault['steady_ns']-p['steady_ns'])
    if not (0<gap<=250_000_000 and a['wall_ns']<=s['wall_ns']<=t and s.get('valid') is True and s['stamp_ns']==a['stamp_ns']==latch['source_stamp_ns'] and abs(excess)>THRESHOLD_NS and abs(mission_excess-excess)<=50_000_000):return result
    # Correlate observed changes only; do not infer Windows/NTP causality.
    observed=[]
    for d in (diagnostic or {}).get('events',[]):
        if d.get('clock') not in ('realtime','system_time','ros_time') or d.get('kind')!=('FORWARD' if excess>0 else 'BACKWARD'):continue
        if d.get('window_end_ns',-1)<a['wall_ns'] or d.get('window_start_ns',t+10**9)>b['wall_ns']:continue
        if not d.get('offset_change_lower_ns',0)-THRESHOLD_NS<=excess<=d.get('offset_change_upper_ns',0)+THRESHOLD_NS:continue
        observed.append(d['clock'])
    result.update(classification='CLOCK_DISCONTINUITY_CORRELATED',source_stamp_delta_ns=stamp_delta,source_steady_delta_ns=gap,source_excess_ns=excess,mission_excess_ns=mission_excess,watchdog_receipt_age_s=age,latch_to_fault_ns=fault['steady_ns']-t,direct_container_clocks=sorted(set(observed)),direct_clock_step_observed=bool(observed),basis='source + mission stamp correlation and native guard witness; not OS origin')
    return result

def inspect_archive(archive,sidecar):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
    from verify_evidence import verify
    receipt=verify(archive,sidecar)
    with tarfile.open(archive,'r:gz') as t:
        names=set(t.getnames())
        def read(name,default=None,lines=False):
            if name not in names:return default
            f=t.extractfile(name)
            if lines:return [json.loads(line) for line in f if line.strip()]
            return json.load(f)
        owner=read('owner-result.json');cases=[]
        paths=sorted(n for n in names if n.startswith('faults/') and n.endswith('/record_result.json') and len(n.split('/'))==3)
        for n in paths:
            prefix=n.rsplit('/',1)[0]+'/'
            rec=read(n);src=read(prefix+'scan_source_trace.json',{});wd=read(prefix+'watchdog_native_trace.json',{});events=read(prefix+'executor/mission-events.jsonl',[],True)
            cases.append(classify(owner,rec,src.get('events',[]),wd.get('events',[]),events,read(prefix+'clock-diagnosis.json',{})))
        return dict(schema=1,archive_sha256=receipt['archive_sha256'],internal_verified=receipt['verified_files'],owner_verdict=owner.get('result'),owner_exit_code=owner.get('exit_code'),cases=cases,classification_only=True,main_merge='NOT_DECIDED_BY_CLASSIFIER')

def main():
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('sidecar',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    result=inspect_archive(a.archive,a.sidecar);payload=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if a.out:
        with a.out.open('x') as f:f.write(payload)
    print(payload,end='')
if __name__=='__main__':main()
