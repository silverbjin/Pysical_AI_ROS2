"""C15: demo String and typed production readers are deliberately separate."""
import argparse,collections,csv,hashlib,json
from pathlib import Path
from analyze_mission import analyze,require

def ns(s):return s.sec*10**9+s.nanosec
def reader(path):
    import rosbag2_py
    r=rosbag2_py.SequentialReader()
    r.open(rosbag2_py.StorageOptions(uri=str(path),storage_id='mcap'),rosbag2_py.ConverterOptions('cdr','cdr'))
    return r,{x.name:x.type for x in r.get_all_topics_and_types()}

def read_states(bag_path):
    from std_msgs.msg import String
    from rclpy.serialization import deserialize_message
    r,types=reader(bag_path);topic='/ch15/mission_state_demo'
    require(types.get(topic)=='std_msgs/msg/String','wrong demo type')
    origin=None;out=[]
    while r.has_next():
        name,data,t=r.read_next()
        if name!=topic:continue
        if origin is None:origin=t
        out.append(dict(record_ns=t,elapsed_record_s=(t-origin)/1e9,state=deserialize_message(data,String).data))
    require(bool(out),'empty demo');return out

def decode(path,config):
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message
    import yaml
    r,types=reader(path);require(types==config['required'],'wrong topic/type allowlist')
    counts=collections.Counter();events=[];states=[];first=None;previous=None
    for_name={k:get_message(v) for k,v in types.items()}
    while r.has_next():
        name,data,t=r.read_next()
        require(previous is None or t>=previous,'record clock rewind');previous=t
        counts[name]+=1
        if first is None:first=t
        m=deserialize_message(data,for_name[name])
        if name=='/ch15/mission_event':
            events.append(dict(record_ns=t,elapsed_record_s=(t-first)/1e9,ros_ns=ns(m.header.stamp),mission_id=m.mission_id,epoch=m.epoch,producer=m.producer,event_seq=m.event_seq,steady_ns=m.steady_ns,event=m.event,request_id=m.request_id,goal_uuid=m.goal_uuid,source=m.source,detail=json.loads(m.detail)))
        elif name=='/ch15/mission_state':
            states.append(dict(record_ns=t,elapsed_record_s=(t-first)/1e9,ros_ns=ns(m.header.stamp),mission_id=m.mission_id,epoch=m.epoch,source=m.source,profile=m.profile,state=m.state,error_code=m.error_code,full_mission_success=m.full_mission_success))
    require(set(counts)==set(types) and min(counts.values())>0,'required topic empty')
    info=yaml.safe_load((path/'metadata.yaml').read_text())['rosbag2_bagfile_information']
    expected={x['topic_metadata']['name']:x['message_count'] for x in info['topics_with_message_count']}
    require(info['storage_identifier']=='mcap' and expected==dict(counts) and sum(counts.values())==info['message_count'],'metadata mismatch')
    metrics=analyze(events,states);metrics.update(topic_counts=dict(counts),storage='mcap')
    return events,states,metrics

def save_csv(path,rows):
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
        for row in rows:w.writerow({k:json.dumps(v,sort_keys=True) if isinstance(v,dict) else v for k,v in row.items()})

def main():
    p=argparse.ArgumentParser();p.add_argument('bag',type=Path);p.add_argument('out',type=Path);p.add_argument('--demo',action='store_true');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    if a.demo:save_csv(a.out/'demo.csv',read_states(a.bag));return
    cfg=json.loads((Path(__file__).resolve().parents[1]/'config/g05_record.json').read_text())
    e,s,m=decode(a.bag,cfg)
    save_csv(a.out/'events.csv',e);save_csv(a.out/'states.csv',s)
    (a.out/'metrics.json').write_text(json.dumps(m,indent=2)+'\n')
if __name__=='__main__':main()
