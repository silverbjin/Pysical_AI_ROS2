"""Independent readiness negatives and narrowly scoped action deadline/latch regression."""
import json,os,pathlib,signal,subprocess,sys,time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import TwistStamped,TransformStamped
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool
from lifecycle_msgs.srv import GetState
from tf2_ros import StaticTransformBroadcaster
from nav2_msgs.action import NavigateToPose
from ch15_interfaces.action import PickObject,PlaceObject
from ch15_interfaces.msg import ReadyState,SafetyState
from ch15_adapters.qos_profiles import profile,sensor_qos,state_qos

out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
rows=[];children=[];exits=[]
def record(label,**data):
    row=dict(label=label,**data);rows.append(row);print(json.dumps(row),flush=True)
def launch(pkg,exe,*args):
    p=pathlib.Path(os.environ['G02_INSTALL'])/pkg/'lib'/pkg/exe
    stream=(out/(exe+'.log')).open('w')
    child=subprocess.Popen([str(p),*args],stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    item=(exe,child,stream);children.append(item);return item
def stop(item):
    name,p,stream=item
    if p.poll() is None:p.send_signal(signal.SIGINT)
    try:rc=p.wait(timeout=6);forced=False
    except subprocess.TimeoutExpired:
        os.killpg(p.pid,signal.SIGKILL);rc=p.wait(timeout=3);forced=True
    stream.close();children.remove(item)
    exits.append(dict(name=name,exit=rc,forced=forced))
    return rc==0 and not forced
rclpy.init();node=Node('ch15_g02_boundary_probe')
ready=[];safety=[];life=[True];scan_on=[True];heartbeat_on=[True]
subs=[node.create_subscription(ReadyState,'/ch15/ready',ready.append,profile()),node.create_subscription(SafetyState,'/ch15/safety_state',safety.append,state_qos)]
scan=node.create_publisher(LaserScan,'/scan',sensor_qos)
heartbeat=node.create_publisher(Bool,'/ch15/stop_request',profile(10))
def get_state(req,res):
    res.current_state.id=3 if life[0] else 2;res.current_state.label='active' if life[0] else 'inactive';return res
service=node.create_service(GetState,'/g02_lifecycle_fixture/get_state',get_state)
def emit():
    if scan_on[0]:
        m=LaserScan();m.header.stamp=node.get_clock().now().to_msg();m.header.frame_id='base_link';m.range_min=.05;m.range_max=5.;m.angle_min=-.5;m.angle_max=.5;m.angle_increment=.5;m.ranges=[2.,2.,2.];scan.publish(m)
    if heartbeat_on[0]:heartbeat.publish(Bool(data=False))
timer=node.create_timer(.05,emit)
def until(pred,seconds=8):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        for name,p,_ in children:assert p.poll() is None,(name,p.returncode)
        rclpy.spin_once(node,timeout_sec=.02)
        if pred():return
    raise AssertionError('deadline: '+str(rows[-1] if rows else 'startup')+' missing='+str(list(ready[-1].missing) if ready else []))
def missing_one(name):
    until(lambda:ready and not ready[-1].ready and list(ready[-1].missing)==[name])
    record('individual_missing_blocked',predicate=name)
def wait_ready():until(lambda:ready and ready[-1].ready)
def pose(p):
    p.header.frame_id='map';p.header.stamp=node.get_clock().now().to_msg();p.pose.position.x=1.;p.pose.orientation.w=1.
def goal(client,req,expected):
    until(client.server_is_ready);f=client.send_goal_async(req);until(f.done);h=f.result()
    if expected=='REJECT':
        assert not h.accepted;record('latched_goal_rejected',action=type(req).__name__);return
    assert h.accepted
    f=h.get_result_async();until(f.done);res=f.result()
    assert res.status==expected,(res.status,expected)
    if hasattr(res.result,'success'):assert res.result.success==(expected==GoalStatus.STATUS_SUCCEEDED)
    if expected==GoalStatus.STATUS_ABORTED:assert res.result.error_message=='deadline'
    record('deadline_or_state_terminal',action=type(req).__name__,status=res.status,uuid=bytes(h.goal_id.uuid).hex(),timeout=getattr(req,'timeout_sec',None))
err=None
try:
    launch('ch15_safety','command_arbiter')
    launch('ch15_safety','readiness_monitor','--ros-args','-p','required_lifecycle_node:=/g02_lifecycle_fixture')
    mock=launch('ch15_adapters','mock_servers','--ros-args','-p','publish_scan:=false','-p','publish_tf:=false')
    start=time.monotonic()
    missing_one('tf')
    tf=StaticTransformBroadcaster(node);t=TransformStamped();t.header.stamp=node.get_clock().now().to_msg();t.header.frame_id='map';t.child_frame_id='base_link';t.transform.rotation.w=1.;tf.sendTransform(t)
    wait_ready();record('initial_ready',wall_s=time.monotonic()-start);assert time.monotonic()-start<15.
    life[0]=False;missing_one('lifecycle');life[0]=True;wait_ready()
    scan_on[0]=False;missing_one('sensor');scan_on[0]=True;wait_ready()
    nav=ActionClient(node,NavigateToPose,'/navigate_to_pose');pick=ActionClient(node,PickObject,'/pick_object');place=ActionClient(node,PlaceObject,'/place_object')
    n=NavigateToPose.Goal();pose(n.pose);goal(nav,n,GoalStatus.STATUS_SUCCEEDED)
    p=PickObject.Goal();p.object_class='red_cube';pose(p.target_pose);p.timeout_sec=.01;goal(pick,p,GoalStatus.STATUS_ABORTED)
    p.timeout_sec=2.;goal(pick,p,GoalStatus.STATUS_SUCCEEDED)
    q=PlaceObject.Goal();pose(q.target_pose);q.timeout_sec=.01;goal(place,q,GoalStatus.STATUS_ABORTED)
    q.timeout_sec=2.;goal(place,q,GoalStatus.STATUS_SUCCEEDED)
    heartbeat_on[0]=False;missing_one('heartbeat');until(lambda:safety and safety[-1].latched and safety[-1].blocked)
    heartbeat_on[0]=True;wait_ready()
    until(lambda:safety and safety[-1].latched and safety[-1].blocked)
    goal(nav,n,'REJECT');goal(pick,p,'REJECT');record('false_heartbeat_does_not_release_latch')
    assert stop(mock)
    dummy=node.create_publisher(TwistStamped,'/ch15/cmd_vel_in',profile())
    missing_one('server')
    assert {r['predicate'] for r in rows if r['label']=='individual_missing_blocked'}=={'tf','lifecycle','sensor','heartbeat','server'}
except BaseException as exc:
    err=repr(exc);record('FAIL',error=err)
finally:
    for item in list(reversed(children)):stop(item)
    node.destroy_node();rclpy.try_shutdown()
    clean=all(x['exit']==0 and not x['forced'] for x in exits)
    result=dict(source='MOCK',full_mission_success=False,result='PASS' if err is None and clean else 'FAIL',error=err,events=rows,processes=exits)
    (out/'boundaries-result.json').write_text(json.dumps(result,indent=2)+'\n')
sys.exit(0 if result['result']=='PASS' else 1)
