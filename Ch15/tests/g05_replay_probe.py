"""Consumer-first actual DDS replay; strict typed graph and exact event data."""
import json,os,sys,subprocess,time,signal
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from replay_contract import validate,SAFE,EndpointAudit,RESTRICTED
from bag_to_csv import reader
import rclpy
from rclpy.node import Node
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.convert import message_to_ordereddict
from rosgraph_msgs.msg import Clock
from ch15_interfaces.msg import MissionEvent,MissionStatus
from ch15_adapters.qos_profiles import profile
bag=Path(sys.argv[1]);out=Path(sys.argv[2]);domain=int(sys.argv[3]);source=int(sys.argv[4])
topics=validate(domain,source,SAFE)
assert os.environ.get('ROS_DOMAIN_ID')==str(domain) and os.environ.get('ROS_LOCALHOST_ONLY')=='1'
rclpy.init();n=Node('g05_replay_consumer');events=[];states=[];clock=[];seen={};p=None;error=None;clock_one=False;player_exit=None;forced=False
expected=[];expected_states=[];endpoint_audit=EndpointAudit();graph_error=None;graph_cleanup=False;clock_monotonic=False;state_payload_exact=False
n.create_subscription(MissionEvent,SAFE[0],events.append,profile(100))
n.create_subscription(MissionStatus,SAFE[1],states.append,profile(10,reliable=False,transient=True))
n.create_subscription(Clock,'/clock',clock.append,profile(10,reliable=False))
def key(m):return json.dumps(message_to_ordereddict(m),sort_keys=True,separators=(',',':'))
def data_complete():
    return bool(expected and expected_states and len(events)==len(expected) and states and key(states[-1])==expected_states[-1] and [key(m) for m in events]==expected)
def graph():
    global clock_one,graph_error
    present=set()
    complete=data_complete()
    for name,types in n.get_topic_names_and_types():
        pubs=n.get_publishers_info_by_topic(name)
        if not pubs:continue
        present.add(name)
        endpoints=[dict(owner=x.node_name,namespace=x.node_namespace,gid=bytes(x.endpoint_gid).hex(),type=x.topic_type) for x in pubs]
        try:
            owners=endpoint_audit.observe(name,types,endpoints,completed=complete)
        except ValueError:
            graph_error=dict(topic=name,types=types,endpoints=endpoints,completed=complete,player_poll=p.poll() if p else None)
            raise
        seen[name]=dict(types=sorted(types),owners=owners)
        if name=='/clock':clock_one=True
    assert not any('_action' in name or '/ch15/start_mission'==name or '/ch15/cancel_mission'==name for name,_ in n.get_service_names_and_types()),'control service discovered'
    return present
try:
    end=time.monotonic()+.5
    while time.monotonic()<end:rclpy.spin_once(n,timeout_sec=.02)
    assert set(n.get_node_names())=={'g05_replay_consumer'},'replay domain not empty'
    r,types=reader(bag)
    assert '/clock' not in types,'recorded clock not permitted for G05 mock'
    assert all(t in types for t in SAFE)
    while r.has_next():
        name,data,t=r.read_next()
        if name==SAFE[0]:expected.append(key(deserialize_message(data,MissionEvent)))
        if name==SAFE[1]:expected_states.append(key(deserialize_message(data,MissionStatus)))
    assert expected and expected_states
    with out.with_suffix('.log').open('w') as log:
        p=subprocess.Popen(['ros2','bag','play',str(bag),'--clock','20','--delay','2','--topics',*topics],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        end=time.monotonic()+45
        while p.poll() is None and time.monotonic()<end:
            rclpy.spin_once(n,timeout_sec=.02);graph()
        player_exit=p.poll();assert player_exit==0,'player exit/deadline'
        end=time.monotonic()+3.
        while time.monotonic()<end:
            rclpy.spin_once(n,timeout_sec=.02)
            present=graph()
            if data_complete() and set(n.get_node_names())=={'g05_replay_consumer'} and not set(RESTRICTED)&present:
                graph_cleanup=True;break
        assert graph_cleanup,'player endpoints not removed'
        assert clock_one and clock and states,'missing clock or state'
        assert [key(m) for m in events]==expected,'event payload/order mismatch'
        expected_set=set(expected_states)
        state_payload_exact=all(key(m) in expected_set for m in states) and key(states[-1])==expected_states[-1]
        assert state_payload_exact,'status payload/final mismatch'
        stamps=[m.clock.sec*10**9+m.clock.nanosec for m in clock]
        clock_monotonic=all(b>=a for a,b in zip(stamps,stamps[1:]))
        assert clock_monotonic,'clock rewind'
except BaseException as e:error=repr(e)
finally:
    if p and p.poll() is None:
        p.send_signal(signal.SIGINT)
        try:player_exit=p.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);player_exit=p.wait(timeout=3);forced=True
    n.destroy_node();rclpy.try_shutdown()
    result=dict(result='PASS' if error is None else 'FAIL',error=error,domain=domain,source_domain=source,topics=sorted(seen),graph=seen,clock_one=clock_one,clock_messages=len(clock),event_count=len(events),state_count=len(states),expected_event_count=len(expected),expected_state_count=len(expected_states),event_payload_exact=bool(expected) and [key(m) for m in events]==expected,player_exit=player_exit,forced=forced,playback_topics=topics,control_publishers=0 if error is None else None,graph_cleanup=graph_cleanup,graph_error=graph_error,endpoint_bindings=endpoint_audit.bound,metadata_loss=endpoint_audit.metadata_loss,state_payload_exact=state_payload_exact,clock_monotonic=clock_monotonic)
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
sys.exit(0 if result['result']=='PASS' else 1)
