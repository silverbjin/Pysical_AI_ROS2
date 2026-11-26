"""Actual DDS messages, shared production decoder, controlled clock fixture."""
import json,os,pathlib,signal,subprocess,sys,time
import py_trees,rclpy
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import String
from tf2_ros import Buffer,TransformListener
from ch15_interfaces.msg import TargetObservation
from ch15_adapters.qos_profiles import profile
from ch15_mission.blackboard_context import BlackboardContext,Target
from ch15_mission.behaviours import PickObjectBehaviour
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
log=(out/'fixture.log').open('w');child=subprocess.Popen([sys.executable,str(pathlib.Path(__file__).with_name('g03_target_fixture.py'))],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
rclpy.init();n=Node('g03_target_probe');received=[];pub=n.create_publisher(String,'/g03/target_command',profile(10))
sub=n.create_subscription(TargetObservation,'/g03/target',received.append,profile(10))
tf=Buffer();listener=TransformListener(tf,n);rows=[];err=None
def until(pred,secs=5.):
    end=time.monotonic()+secs
    while time.monotonic()<end:
        assert child.poll() is None
        rclpy.spin_once(n,timeout_sec=.01)
        if pred():return
    raise AssertionError('deadline')
def send(case,**changes):
    data=dict(case=case,mission_id='m',epoch=1,frame='map',stamp_ns=950000000)
    data.update(changes);pub.publish(String(data=json.dumps(data)));until(lambda:any(x.reason==case for x in received))
    return next(x for x in received if x.reason==case)
def tf_ok():return tf.can_transform('map','base_link',Time())
class Spy:
    def __init__(self):self.sends=0
    def ready_for_goal(self):return True
    def send(self,g):self.sends+=1;raise AssertionError('invalid pick sent')
def negative(case,msg,bb):
    now=time.monotonic();assert not bb.write_observation(msg,tf_ok(),now)
    reason=bb.reason;assert bb.read(now,tf_ok()) is None
    spy=Spy();b=PickObjectBehaviour('pick',spy,lambda:bb.read(time.monotonic(),tf_ok()));b.tick_once()
    assert b.status==py_trees.common.Status.FAILURE and spy.sends==0
    row=dict(case=case,result='REJECTED',reason=reason,pick_sends=0,snapshot=False);rows.append(row);print(json.dumps(row),flush=True)
def seed():
    bb=BlackboardContext('m',1);now=time.monotonic();bb.clock(1000000000,now)
    assert bb.write_target(Target('m',1,'MOCK','red_cube','map',950000000,(1.,0.,.225),(0.,0.,0.,1.),'GRASP_POSE',now),True,now)
    return bb
try:
    until(lambda:pub.get_subscription_count()==1 and n.count_publishers('/g03/target')==1)
    assert not tf_ok()
    negative('missing_tf',send('missing_tf'),seed())
    pub.publish(String(data='{"tf":true}'));until(tf_ok)
    good=send('normal');bb=seed()
    assert bb.write_observation(good,tf_ok(),time.monotonic());assert bb.snapshot.stamp_ns==950000000
    rows.append(dict(case='normal',result='ACCEPTED',stamp_ns=bb.snapshot.stamp_ns));print(json.dumps(rows[-1]),flush=True)
    for name,changes in [('stale',{'stamp_ns':699999999}),('future',{'stamp_ns':1000000001}),('zero',{'stamp_ns':0}),('wrong_frame',{'frame':'odom'}),('old_mission',{'mission_id':'old'}),('wrong_epoch',{'epoch':0}),('nonfinite',{'nonfinite':True})]:
        msg=send(name,**changes);negative(name,msg,seed())
    for name in ('pause','rewind'):
        msg=send(name);bb=seed();now=time.monotonic()
        if name=='pause':bb.clock(1000000000,now+.21)
        else:bb.clock(1100000000,now+.01);bb.clock(1000000000,now+.02)
        negative(name,msg,bb)
    assert len(rows)==11 and sum(x['result']=='REJECTED' for x in rows)==10
except BaseException as e:err=repr(e);print(err,flush=True)
finally:
    if child.poll() is None:child.send_signal(signal.SIGINT)
    forced=False
    try:rc=child.wait(timeout=6.)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);rc=child.wait(timeout=3);forced=True
    log.close();n.destroy_node();rclpy.try_shutdown()
    result=dict(result='PASS' if err is None and rc==0 and not forced else 'FAIL',error=err,cases=rows,clock='controlled ROS timestamp fixture; actual DDS and TF',process=dict(exit=rc,forced=forced))
    (out/'target-result.json').write_text(json.dumps(result,indent=2)+'\n')
sys.exit(0 if result['result']=='PASS' else 1)
