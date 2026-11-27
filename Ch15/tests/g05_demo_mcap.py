"""Actual MCAP writer/reader; synthetic demo data, not a live mission."""
import gc,json,sys
from pathlib import Path
import rosbag2_py as rb
from rclpy.serialization import serialize_message
from std_msgs.msg import String,Bool
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from bag_to_csv import read_states,decode

def make(path,typ,msgs):
    w=rb.SequentialWriter()
    w.open(rb.StorageOptions(uri=str(path),storage_id='mcap'),rb.ConverterOptions('cdr','cdr'))
    topic='/ch15/mission_state_demo'
    w.create_topic(rb.TopicMetadata(id=0,name=topic,type=typ,serialization_format='cdr',offered_qos_profiles=[]))
    for i,m in enumerate(msgs):w.write(topic,serialize_message(m),1_000_000_000+i*100_000_000)
    if hasattr(w,'close'):w.close()
    del w;gc.collect()
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
make(out/'demo','std_msgs/msg/String',[String(data='S'+str(i)) for i in range(1,11)])
rows=read_states(out/'demo')
assert [r['state'] for r in rows]==['S'+str(i) for i in range(1,11)]
assert abs(rows[-1]['elapsed_record_s']-.9)<=1e-9
make(out/'wrong','std_msgs/msg/Bool',[Bool(data=True)])
try:read_states(out/'wrong')
except ValueError as e:assert str(e)=='wrong demo type'
else:raise AssertionError('wrong demo type accepted')
try:decode(out/'demo',json.loads((ROOT/'config/g05_record.json').read_text()))
except ValueError as e:assert str(e)=='wrong topic/type allowlist'
else:raise AssertionError('String demo accepted as typed mission')
print(json.dumps(dict(result='PASS',scope='actual MCAP CDR synthetic fixture',demo_messages=10,elapsed_record_s=rows[-1]['elapsed_record_s'],wrong_demo_type_rejected=True,demo_as_typed_rejected=True)))
(out/'demo_result.json').write_text(json.dumps(dict(result='PASS',demo_messages=10,elapsed_record_s=rows[-1]['elapsed_record_s'],wrong_demo_type_rejected=True,demo_as_typed_rejected=True),indent=2)+'\n')
