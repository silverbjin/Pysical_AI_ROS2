#!/usr/bin/env python3
"""Opt-in Ch15 basic BT/MCAP integration; original physical guards and assessor."""
import argparse,collections,hashlib,json,signal,subprocess,sys,threading,time,traceback
from pathlib import Path
from table_l2_contract import TOPICS,N,bag_checks,goal_audit,goal_trace_matches

def audit_bag(path,discovered):
    import yaml,rosbag2_py
    from rclpy.serialization import deserialize_message
    from geometry_msgs.msg import TwistStamped
    from std_msgs.msg import String
    meta=yaml.safe_load((path/'metadata.yaml').read_text())['rosbag2_bagfile_information']
    assert meta['storage_identifier']=='mcap'
    files=meta['relative_file_paths']
    assert files and all((path/f).is_file() and (path/f).stat().st_size>0 and f.endswith('.mcap') for f in files)
    reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(path),storage_id='mcap'),rosbag2_py.ConverterOptions('cdr','cdr'))
    counts=collections.Counter();starts=[];motion=[];success=[]
    while reader.has_next():
        topic,data,stamp=reader.read_next();counts[topic]+=1
        if topic=='/start_mission':starts.append(stamp)
        elif topic==N+'/cmd_vel_safe':
            v=deserialize_message(data,TwistStamped).twist
            if abs(v.linear.x)>1e-9 or abs(v.angular.z)>1e-9:motion.append(stamp)
        elif topic==N+'/validation/bt_log':
            value=json.loads(deserialize_message(data,String).data)
            if value.get('terminal')=='SUCCESS':success.append(stamp)
    metadata_counts={r['topic_metadata']['name']:r['message_count'] for r in meta['topics_with_message_count']}
    checks=bag_checks(counts,metadata_counts,starts,motion,success,discovered)
    checks['metadata_total']=sum(counts.values())==meta['message_count']
    def file_record(f):
        with (path/f).open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
        return dict(name=f,bytes=(path/f).stat().st_size,sha256=digest)
    return dict(result='PASS' if all(checks.values()) else 'FAIL',checks=checks,
                counts=dict(counts),start_stamps=starts,first_motion=min(motion) if motion else None,
                last_motion=max(motion) if motion else None,terminal_stamps=success,
                mcap_files=[file_record(f) for f in files])

class Bridge:
    """Only robot worker owns goal futures; BT owner sees TaskPort snapshots."""
    def __init__(self,port):
        self.port=port;self.ready=threading.Event();self.futures=[];self.rows=[];self.session=None;self.session_status=None
    def bind_session(self,status):
        self.session_status=status;self.session=status().get('session');self.validate_session()
    def validate_session(self):
        status=self.session_status() if self.session_status else {}
        assert self.session and status.get('session')==self.session and not status.get('fault'),'actual session changed/faulted'
    def cancel_requested(self):return bool(self.port.snapshot()['cancel_reason'])
    def before_survey(self,until):
        self.ready.set()
        self.await_step('navigate',until)
    def await_step(self,name,until):
        assert until(lambda:name in self.port.snapshot()['requested'] or self.cancel_requested(),30),'BT task deadline '+name
        assert not self.cancel_requested(),'BT canceled'
        self.validate_session();self.port.event('started',task=name,session=self.session)
    def goal_sent(self,sent):self.futures.append(dict(sent=sent,handle=None,row=None,result=None))
    def poll_goals(self):
        for x in self.futures:
            if x['handle'] is None and x['sent'].done():
                h=x['sent'].result()
                if not h.accepted:
                    x['handle']=h;x['row']={'goal_id':None,'terminal':6};self.rows.append(x['row']);continue
                x['handle']=h;x['row']={'goal_id':bytes(h.goal_id.uuid).hex()}
                self.rows.append(x['row'])
    def goal_terminal(self,h,terminal):
        self.poll_goals()
        row=next(r for r in self.rows if r.get('goal_id')==bytes(h.goal_id.uuid).hex())
        if 'terminal' in row and row['terminal']!=terminal:raise RuntimeError('terminal changed')
        row['terminal']=terminal
    def navigated(self,until,s,clock):
        assert not self.cancel_requested();self.validate_session()
        self.port.complete('navigate',dict(position_error_m=s['final_xy_error_m'],yaw_error_rad=s['final_yaw_error_rad'],
            goal_id=s['handoff']['nav2_terminal_uuid'],clock_ns=clock,session=self.session,source='actual fixed-world settled V3'))
        self.await_step('find',until)
    def found(self,until,observation,clock,s):
        from ch13_mission_orchestration.session import admit_observation
        assert not self.cancel_requested();self.validate_session()
        self.port.complete('find',dict(observation=admit_observation(observation,clock,time.monotonic()),workspace=s['checks']['workspace'],session=self.session))
        self.await_step('finish',until)
    def audit(self):
        a=goal_audit(self.rows)
        a['pending']+=sum(x['row'] is None for x in self.futures)
        return a

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo-root',required=True);p.add_argument('--manifest',required=True);p.add_argument('--evidence',required=True)
    a=p.parse_args();out=Path(a.evidence).resolve()
    # Robot worker creates its own segment directory. Mission recording uses
    # a sibling temporary directory, then joins evidence after worker exit.
    assert not out.exists()
    work=out.with_name(out.name+'_mission');work.mkdir(parents=True,exist_ok=False)
    import rclpy,py_trees
    from rclpy.context import Context
    from rclpy.node import Node
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.signals import SignalHandlerOptions
    from std_msgs.msg import Empty,String
    from rosgraph_msgs.msg import Clock
    from ch13_mission_orchestration.tasks import TaskPort,STEPS
    from ch13_mission_orchestration.tree import Mission
    from ch13_system_validation.basic_exercise import configure_tasks,assess_basic
    from ch13_system_validation.scenarios import get_scenario
    from ch13_system_validation.world_assessment import assess_world
    from ch13_system_validation.telemetry import LiveStatusWriter
    from run_table_segment import main as robot
    port=TaskPort(STEPS+('place',));mission=Mission(port);configure_tasks(mission,'basic')
    bridge=Bridge(port);status=LiveStatusWriter(work/'live_status.json');worker_result={};discovered=[]
    context=Context();rclpy.init(context=context,signal_handler_options=SignalHandlerOptions.NO)
    node=Node('ch15_table_bt',context=context);ex=SingleThreadedExecutor(context=context);ex.add_node(node)
    pub=node.create_publisher(String,N+'/validation/bt_log',1)
    start_pub=node.create_publisher(Empty,'/start_mission',1)
    clock=[0];started=[False]
    def on_clock(msg):clock[0]=msg.clock.sec*1_000_000_000+msg.clock.nanosec
    node.create_subscription(Clock,'/clock',on_clock,1)
    def start(_):
        if started[0]:port.fail('duplicate start_mission');port.cancel('duplicate_start');return
        if not sent_start or set(discovered)!=set(TOPICS) or clock[0]<=0 or node.count_publishers('/start_mission')!=1:
            port.fail('start before recorder admission or unexpected publisher');port.cancel('start_not_admitted');return
        started[0]=True;port.event('start_mission_received',clock_ns=clock[0])
    node.create_subscription(Empty,'/start_mission',start,1)
    def tick():
        if not started[0] and not port.snapshot()['error']:return
        previous=len(mission.ticks);mission.tick()
        if len(mission.ticks)>previous:
            value=mission.ticks[-1];pub.publish(String(data=json.dumps(value)))
            status.offer(dict(terminal=mission.terminal,clock_ns=clock[0],port=port.snapshot()))
    node.create_timer(.1,tick)
    bag_log=(work/'bag.log').open('w')
    bag=subprocess.Popen(['/usr/bin/python3','/opt/ros/jazzy/bin/ros2','bag','record','--storage','mcap','--use-sim-time','-o',str(work/'bag'),*TOPICS],
                         stdout=bag_log,stderr=subprocess.STDOUT,start_new_session=True)
    def worker():
        code=1
        try:
            code=robot(['--repo-root',a.repo_root,'--manifest',a.manifest,'--evidence',str(out)],mission=bridge)
            worker_result['exit_code']=code
            if code:port.fail('actual robot segment failed')
            elif not bridge.cancel_requested():port.complete('finish',dict(source='actual engine and children closed',session=bridge.session))
        except BaseException:
            worker_result['exception']=traceback.format_exc();port.fail(worker_result['exception'])
        finally:port.close(code)
    thread=threading.Thread(target=worker,name='ch15_bt_owned_robot',daemon=False);thread.start()
    begin=time.monotonic();sent_start=False;bag_closed=False;err=None
    def interrupt(*_):port.cancel('operator_cancel')
    old=signal.signal(signal.SIGINT,interrupt)
    try:
        while thread.is_alive() or mission.terminal is None:
            ex.spin_once(timeout_sec=.05)
            if bag.poll() is not None:port.fail('recorder exited early');port.cancel('recorder_exit')
            if bridge.ready.is_set() and not sent_start and not bridge.cancel_requested() and not port.snapshot()['error']:
                discovered=[t for t in TOPICS if any(i.node_name=='rosbag2_recorder' for i in node.get_subscriptions_info_by_topic(t))]
                if set(discovered)==set(TOPICS) and clock[0]>0 and node.count_publishers('/start_mission')==1:
                    sent_start=True;start_pub.publish(Empty())
                elif time.monotonic()-begin>60:port.fail('recorder discovery deadline');port.cancel('recorder_discovery')
            if time.monotonic()-begin>1200:port.fail('mission wall budget');port.cancel('wall_budget')
            if time.monotonic()-begin>1230:raise RuntimeError('worker did not drain')
        thread.join(timeout=5)
        # Let the last actual BT tick reach the recorder before SIGINT.
        end=time.monotonic()+.5
        while time.monotonic()<end:ex.spin_once(timeout_sec=.05)
    except BaseException:
        err=traceback.format_exc();port.fail(err);port.cancel('mission_exception')
        thread.join(timeout=30)
    finally:
        signal.signal(signal.SIGINT,old)
        if bag.poll() is None:bag.send_signal(signal.SIGINT)
        try:bag.wait(timeout=15);bag_closed=bag.returncode==0
        except subprocess.TimeoutExpired:bag.terminate();bag.wait(timeout=5)
        bag_log.close();telemetry=status.close();node.destroy_node();ex.shutdown();context.try_shutdown()
    out.mkdir(parents=True,exist_ok=True)
    import shutil
    for item in work.iterdir():shutil.move(str(item),str(out/item.name))
    work.rmdir()
    data=port.snapshot();bt=dict(profile='actual',terminal=mission.terminal,worker_joined=not thread.is_alive(),
        port=data,worker=worker_result,goals=bridge.audit(),session=bridge.session,error=err)
    (out/'bt_summary.json').write_text(json.dumps(bt,indent=2)+'\n')
    (out/'bt_ticks.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in mission.ticks))
    (out/'telemetry_delivery.json').write_text(json.dumps(telemetry,indent=2)+'\n')
    try:bag_receipt=audit_bag(out/'bag',discovered)
    except BaseException:bag_receipt=dict(result='FAIL',error=traceback.format_exc())
    (out/'mcap_audit.json').write_text(json.dumps(bag_receipt,indent=2)+'\n')
    def read(name):
        f=out/name;return json.loads(f.read_text()) if f.exists() else {}
    seg=read('segment_result.json');engine=read('engine.json');children=seg.get('children',{})
    manipulation=engine.get('manipulation',{})
    no_actions=bool(engine) and engine.get('arm_events')==[] and manipulation.get('arm_events')==[] and manipulation.get('gripper_force_events')==[]
    nav=dict(result='PASS' if seg.get('result')=='PASS_SCOPED_TABLE_SEGMENT' else 'FAIL',
        owned_launch_pids=children.get('pids',[]),clean_launch_exits=children.get('clean',0),remaining_launch_pids=children.get('remaining',[]),launch_exit_code=children.get('launch_exit'),
        manipulation_handoff=dict(exercise='basic',manipulation_executed=not no_actions))
    (out/'navigation_summary.json').write_text(json.dumps(nav,indent=2)+'\n')
    world=assess_world(engine.get('pick_physics',{}).get('rows',[]),get_scenario('level2_obstacles'),found='find' in data['completed'])
    grade=assess_basic(bt,nav,engine,recording_complete=bag_closed and bag_receipt.get('result')=='PASS',
        telemetry_joined=telemetry.get('joined') is True and telemetry.get('write_errors')==0,
        world_pass=world.get('result')=='PASS',manipulation_artifacts=not no_actions or any((out/n).exists() for n in ('arm_probe.json','pick_mission.json')))
    from table_engine_audit import audit_phases
    try:
        native_rows=[json.loads(line) for line in (out/'engine_observations.jsonl').read_text().splitlines()]
        independent=audit_phases(native_rows,seg['phases'],seg['entry_goal'],seg['final_goal'],engine)
    except BaseException:independent=dict(result='FAIL',error=traceback.format_exc())
    (out/'independent_engine_audit.json').write_text(json.dumps(independent,indent=2)+'\n')
    grade['original_basic_assessor_result']=grade['result']
    session_ok=bool(bridge.session and seg.get('mission_session')==bridge.session==manipulation.get('last_status',{}).get('session') and all(data['completed'].get(k,{}).get('session')==bridge.session for k in ('navigate','find','finish')))
    grade['session_contract']=session_ok
    grade['exact_goal_trace']=goal_trace_matches(bt['goals'],seg.get('phases',[]))
    if independent.get('result')!='PASS' or not session_ok or not grade['exact_goal_trace']:grade['result']='FAIL'
    grade.update(independent_engine_audit=independent.get('result'),source='CH15_TABLE_V3_BT',original_native_l2_pass=False,world=world,bag_closed=bag_closed,actual_table_segment=nav['result'],
        segment_checks=seg.get('checks',{}),mission_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'basic_result.json').write_text(json.dumps(grade,indent=2)+'\n');print(json.dumps(grade,indent=2),flush=True)
    return 0 if grade['result']=='PASS' else 1
if __name__=='__main__':sys.exit(main())
