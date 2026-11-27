"""Consumer-first actual DDS replay; observation topics only."""
import json,os,sys,subprocess,time,signal
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from replay_contract import validate,SAFE
from bag_to_csv import reader
import rclpy
from rclpy.node import Node
from rosgraph_msgs.msg import Clock
from ch15_interfaces.msg import MissionEvent,MissionStatus
from ch15_adapters.qos_profiles import profile,state_qos
bag=Path(sys.argv[1]);out=Path(sys.argv[2]);domain=int(sys.argv[3]);source=int(sys.argv[4])
topics=validate(domain,source,SAFE)
assert os.environ.get('ROS_DOMAIN_ID')==str(domain) and os.environ.get('ROS_LOCALHOST_ONLY')=='1'
rclpy.init();n=Node('g05_replay_consumer');events=[];states=[];clock=[];seen=set();p=None;error=None;clock_one=False
n.create_subscription(MissionEvent,SAFE[0],events.append,profile(100))
n.create_subscription(MissionStatus,SAFE[1],states.append,profile(10,reliable=False,transient=True))
n.create_subscription(Clock,'/clock',clock.append,profile(10,reliable=False))
try:
    end=time.monotonic()+.5
    while time.monotonic()<end:rclpy.spin_once(n,timeout_sec=.02)
    assert set(n.get_node_names())=={'g05_replay_consumer'},'replay domain not empty'
    r,types=reader(bag);expected=[]
    from rclpy.serialization import deserialize_message
    while r.has_next():
        name,data,t=r.read_next()
        if name==SAFE[0]:
            m=deserialize_message(data,MissionEvent);expected.append((m.mission_id,m.epoch,m.event_seq))
    with out.with_suffix('.log').open('w') as log:
        p=subprocess.Popen(['ros2','bag','play',str(bag),'--clock','20','--delay','2','--topics',*topics],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        end=time.monotonic()+45
        while p.poll() is None and time.monotonic()<end:
            rclpy.spin_once(n,timeout_sec=.02)
            for name,types in n.get_topic_names_and_types():
                if n.count_publishers(name):seen.add(name)
            if n.count_publishers('/clock')==1:clock_one=True
            assert n.count_publishers('/clock')<=1
            assert seen<=set(topics)|{'/clock','/rosout','/parameter_events'},seen
            assert not any('_action' in name for name,_ in n.get_service_names_and_types()),'action service discovered'
        assert p.poll()==0,'player exit/deadline'
        end=time.monotonic()+.5
        while time.monotonic()<end:rclpy.spin_once(n,timeout_sec=.02)
        assert clock_one and clock and states and [(m.mission_id,m.epoch,m.event_seq) for m in events]==expected
except BaseException as e:error=repr(e)
finally:
    if p and p.poll() is None:
        p.send_signal(signal.SIGINT)
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=3)
    n.destroy_node();rclpy.try_shutdown()
    result=dict(result='PASS' if error is None else 'FAIL',error=error,domain=domain,source_domain=source,topics=sorted(seen),clock_one=clock_one,clock_messages=len(clock),event_count=len(events),state_count=len(states),expected_event_count=len(expected) if 'expected' in locals() else None)
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
sys.exit(0 if result['result']=='PASS' else 1)
