"""Independent actual MCAP and trace acceptance. G05 analyze_mission contract reused."""
import json,sys,csv,hashlib
from pathlib import Path
from collections import Counter
from bag_to_csv import reader,ns,save_csv
from analyze_mission import analyze
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
import yaml
p=Path(sys.argv[1]);mode=sys.argv[2]
cfg=json.loads((Path(__file__).resolve().parents[1]/'config/g08_record.json').read_text())
r,types=reader(p/'bag');assert types==cfg['required'],types
counts=Counter();events=[];states=[];first=None;previous=None;targets=[]
for_name={k:get_message(v) for k,v in types.items()}
while r.has_next():
    name,data,t=r.read_next();assert previous is None or t>=previous;previous=t
    counts[name]+=1
    if first is None:first=t
    m=deserialize_message(data,for_name[name])
    if name=='/ch15/mission_event':
        events.append(dict(record_ns=t,elapsed_record_s=(t-first)/1e9,ros_ns=ns(m.header.stamp),mission_id=m.mission_id,epoch=m.epoch,producer=m.producer,event_seq=m.event_seq,steady_ns=m.steady_ns,event=m.event,request_id=m.request_id,goal_uuid=m.goal_uuid,source=m.source,detail=json.loads(m.detail)))
    elif name=='/ch15/mission_state':
        states.append(dict(record_ns=t,elapsed_record_s=(t-first)/1e9,ros_ns=ns(m.header.stamp),mission_id=m.mission_id,epoch=m.epoch,source=m.source,profile=m.profile,state=m.state,error_code=m.error_code,full_mission_success=m.full_mission_success))
    elif name=='/ch15/target_observation':targets.append(dict(stamp_ns=ns(m.header.stamp),epoch=m.epoch,mission_id=m.mission_id))
info=yaml.safe_load((p/'bag/metadata.yaml').read_text())['rosbag2_bagfile_information']
expected={x['topic_metadata']['name']:x['message_count'] for x in info['topics_with_message_count']}
assert info['storage_identifier']=='mcap' and all(counts[k]==expected[k] for k in types) and sum(counts.values())==info['message_count']
assert all(counts[k]>0 for k in types if k!='/ch15/target_observation')
metrics=analyze(events,states)
orig=[json.loads(s) for s in (p/'executor/mission-events.jsonl').read_text().splitlines()]
assert len(orig)==len(events)
for a,b in zip(events,orig):assert all(a[k]==v for k,v in b.items())
fixture=json.loads((p/'mock_native_trace.json').read_text());audit=[json.loads(s) for s in (p/'executor/target-audit.jsonl').read_text().splitlines()]
receipt=json.loads((p/'fault_receipt.json').read_text());record=json.loads((p/'record_result.json').read_text());assert record['result']=='PASS' and record['terminal']==metrics['terminal']
def e(kind,step):return [x for x in events if x['event']==kind and x['detail'].get('step')==step]
def attempts(step):return [x['detail']['attempt'] for x in e('RECOVERY_ATTEMPT',step)]
def prepared(step):return e('RECOVERY_PREPARED',step)
for x in prepared('detect')+prepared('pick_retract'):
    d=x['detail'];assert d['stamp_ns']>d['settle_ns'] and d['fresh'] and d['settled'] and d['previous_terminal']
    assert any(a['valid'] and a['stamp_ns']==d['stamp_ns'] for a in audit)
pick=[x for x in fixture if x['kind']=='goal_admission' and x['action']=='pick']
terminal=[x for x in events if x['event']=='GOAL_TERMINAL']
if mode=='F03_transient':
    assert attempts('detect')==[1,2] and len(e('RECOVERY_MISS','detect'))==1 and len(prepared('detect'))==1 and len(pick)==1 and metrics['terminal']=='COMPLETED'
    assert any(x['kind']=='target_withheld' and x['attempt']==1 for x in fixture)
    assert any(x['kind']=='target_published' and x['state']=='SEARCHING' for x in fixture)
elif mode=='F03_persistent':
    assert attempts('detect')==[1,2,3] and len(e('RECOVERY_MISS','detect'))==3 and not prepared('detect') and not pick and not targets and metrics['terminal']=='ABORTED'
    assert all(any(x['kind']=='target_withheld' and x['attempt']==i for x in fixture) for i in (1,2,3))
elif mode=='F04':
    assert any(a['reason']=='mission_epoch' and not a['valid'] and a['observation_epoch']!=a['epoch'] for a in audit) and not pick and metrics['terminal']=='ABORTED'
    assert any(t['epoch']!=events[0]['epoch'] for t in targets)
elif mode=='F06':
    assert attempts('pick_retract')==[1,2,3] and len(prepared('pick_retract'))==3 and len(pick)==3 and metrics['terminal']=='ABORTED'
    faults=[x for x in fixture if x['kind']=='pick_fault']
    assert len(faults)==3 and len({x['uuid'] for x in faults})==3 and all(x['success'] is False for x in faults)
    results=e('RECOVERY_RESULT','pick_retract')
    assert [x['detail']['outcome'] for x in results]==['RETRY','RETRY','ABORT']
    for i,(f,x) in enumerate(zip(faults,results)):
        term=next(t for t in terminal if t['goal_uuid']==f['uuid'])
        assert term['detail']['status']==6 and term['steady_ns']<=x['steady_ns'] and x['detail']['prior_uuid']==f['uuid']
        if i<2:assert term['steady_ns']<e('RECOVERY_ATTEMPT','pick_retract')[i+1]['steady_ns']
elif mode=='F01':
    assert metrics['terminal']=='ABORTED' and not pick and len(terminal)==1
    assert any(x['event']=='STOP_OBSERVED' for x in events)
else:raise ValueError(mode)
receipt.update(injection_observed=True,result='PASS')
(p/'fault_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
metrics.update(result='PASS',topic_counts={k:counts[k] for k in types},fault_id=receipt['fault']['fault_id'],run_id=receipt['run_id'],fixture_sha256=receipt['fixture_sha256'],detect_attempts=attempts('detect'),pick_attempts=attempts('pick_retract'),pick_goals=len(pick),exact_event_payloads=len(events),target_count=len(targets),clean_exits=len(record['processes']))
(p/'analysis').mkdir();save_csv(p/'analysis/events.csv',events);save_csv(p/'analysis/states.csv',states)
(p/'analysis/metrics.json').write_text(json.dumps(metrics,indent=2,allow_nan=False)+'\n')
print(json.dumps(metrics))
