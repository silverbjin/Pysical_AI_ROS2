"""Replay sensor/BT records into analysis domain136, never actuator authority."""
import argparse,json,os,signal,subprocess,sys,time
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--bag',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();bag=Path(args.bag).resolve();out=Path(args.output).resolve();log=out.with_suffix('.log')
    if out.exists() or log.exists():raise ValueError('new replay output and log required')
    if not (bag/'metadata.yaml').is_file():raise ValueError('closed bag metadata required')
    os.environ['ROS_DOMAIN_ID']='136'
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile,ReliabilityPolicy
    from std_msgs.msg import String
    from rosgraph_msgs.msg import Clock
    from tf2_msgs.msg import TFMessage
    n='/ch13/reuse';selected=['/tf_static',n+'/vision/observation',n+'/vision/health',n+'/validation/bt_log']
    counts={key:0 for key in selected+['/clock']};captures=[];clocks=[]
    rclpy.init(args=[]);node=Node('ch13_offline_replay_receiver');qos=QoSProfile(depth=100,reliability=ReliabilityPolicy.BEST_EFFORT)
    def receive(topic,message):
        counts[topic]+=1
        if topic==n+'/vision/observation':captures.append(json.loads(message.data)['capture_ns'])
        if topic=='/clock':clocks.append(message.clock.sec*1_000_000_000+message.clock.nanosec)
    for topic in selected+['/clock']:
        kind=Clock if topic=='/clock' else (TFMessage if topic=='/tf_static' else String)
        node.create_subscription(kind,topic,lambda msg,key=topic:receive(key,msg),qos)
    process=None;started=time.monotonic();timed_out=False
    try:
        with log.open('x') as stream:
            process=subprocess.Popen(['/usr/bin/python3','/opt/ros/jazzy/bin/ros2','bag','play',str(bag),
                '--rate','10','--clock','--topics',*selected],stdout=stream,stderr=subprocess.STDOUT)
            while process.poll() is None:
                rclpy.spin_once(node,timeout_sec=.02)
                if time.monotonic()-started>45.:
                    timed_out=True;process.send_signal(signal.SIGINT);process.wait(timeout=5.);break
            end=time.monotonic()+.25
            while time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.01)
    finally:
        if process is not None and process.poll() is None:process.terminate();process.wait(timeout=5.)
        node.destroy_node();rclpy.try_shutdown()
    checks=dict(player_exit=process is not None and process.returncode==0,not_timed_out=not timed_out,
        all_selected_received=all(counts.values()),original_capture_stamps=bool(captures) and all(type(v) is int and v>0 for v in captures),
        advancing_player_clock=len(clocks)>1 and clocks[-1]>clocks[0])
    result=dict(result='PASS' if all(checks.values()) else 'FAIL',checks=checks,domain_id=136,counts=counts,
        selected_topics=selected,first_capture_ns=captures[0] if captures else None,last_capture_ns=captures[-1] if captures else None,
        wall_s=time.monotonic()-started,scope='sensor/BT replay reception only; no engine, controller, live lease or mission performance claim')
    with out.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result,indent=2));return 0 if result['result']=='PASS' else 1


if __name__=='__main__':sys.exit(main())
