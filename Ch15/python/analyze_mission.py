"""Strict typed event contract and clock-separated KPI; no ROS dependency."""
import math,collections

def require(ok,reason):
    if not ok:raise ValueError(reason)

def analyze(events,statuses):
    require(bool(events) and bool(statuses),'missing events/status')
    keys={(r['mission_id'],r['epoch'],r['source']) for r in events+statuses}
    require(len(keys)==1,'mixed mission/epoch/source')
    mission,epoch,source=next(iter(keys))
    require(bool(mission) and source=='MOCK','unsupported source')
    require(all(r['profile']=='mock' and r['full_mission_success'] is False for r in statuses),'profile drift')
    require(all(r['record_ns']>=0 and r['ros_ns']>0 for r in events+statuses),'invalid clock')
    for group in (events,statuses):
        require(all(b['record_ns']>=a['record_ns'] and b['ros_ns']>=a['ros_ns'] for a,b in zip(group,group[1:])),'clock rewind')
    by=collections.defaultdict(list)
    for e in events:by[e['producer']].append(e)
    require(set(by)=={'ch15_mission_executor'},'unexpected producer')
    for group in by.values():
        require([r['event_seq'] for r in group]==list(range(1,len(group)+1)),'event sequence duplicate/gap')
        require(all(b['steady_ns']>=a['steady_ns']>0 for a,b in zip(group,group[1:])),'steady clock rewind')
    require(events[0]['event']=='START' and events[-1]['event']=='END' and sum(e['event']=='START' for e in events)==sum(e['event']=='END' for e in events)==1,'START/END pair')
    sent={};accepted={};term={}
    for e in events:
        name=e['event'];rid=e['request_id'];uid=e['goal_uuid']
        if name=='GOAL_SENT':
            require(rid and rid not in sent,'duplicate send');sent[rid]=e['detail']['requested_uuid']
        if name=='GOAL_ACCEPTED':
            require(rid in sent and rid not in accepted and uid==sent[rid] and len(uid)==32,'accepted UUID mismatch');accepted[rid]=uid
        if name=='GOAL_TERMINAL':
            require(rid in accepted and rid not in term and accepted[rid]==uid and e['detail']['status'] in (4,5,6),'terminal mismatch');term[rid]=uid
    require(sent==accepted==term and len(set(accepted.values()))==len(accepted),'unresolved/duplicate goal')
    end=events[-1]['detail'];state=end['state']
    require(end['all_terminal'] is True and state in ('COMPLETED','ABORTED') and statuses[-1]['state']==state and end['mock_mission_success']==(state=='COMPLETED') and end['full_mission_success'] is False,'terminal contract')
    return dict(mission_id=mission,epoch=epoch,source=source,terminal=state,events=len(events),statuses=len(statuses),goals=len(term),elapsed_steady_s=(events[-1]['steady_ns']-events[0]['steady_ns'])/1e9,elapsed_record_s=(events[-1]['record_ns']-events[0]['record_ns'])/1e9,elapsed_ros_s=(events[-1]['ros_ns']-events[0]['ros_ns'])/1e9,energy_j=None,energy_reason='no joint effort/velocity in mock recording',full_mission_success=False)

def energy_j(samples):
    # Trapezoidal integral of absolute mechanical power; missing data is unknown.
    if len(samples)<2:return None
    power=[]
    for stamp,effort,velocity in samples:
        if not effort or len(effort)!=len(velocity) or not all(math.isfinite(x) for x in (*effort,*velocity)):return None
        power.append((stamp,sum(abs(a*b) for a,b in zip(effort,velocity))))
    require(all(b[0]>a[0] for a,b in zip(power,power[1:])),'joint clock rewind')
    return sum((b[0]-a[0])/1e9*(a[1]+b[1])/2 for a,b in zip(power,power[1:]))
