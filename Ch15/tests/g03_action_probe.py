"""Real DDS action supervisor 8 boundary cases; one independent fixture."""
import json,pathlib,subprocess,signal,sys,time,os
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from unique_identifier_msgs.msg import UUID
from std_msgs.msg import String
from ch15_interfaces.action import PickObject
from ch15_adapters.qos_profiles import profile
from ch15_mission.action_supervisor import ActionSupervisor
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
log=(out/'fixture.log').open('w')
child=subprocess.Popen([sys.executable,str(pathlib.Path(__file__).with_name('g03_action_fixture.py'))],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
rclpy.init();n=Node('g03_action_probe');c=ActionClient(n,PickObject,'/g03/action');witness=set();sub=n.create_subscription(String,'/g03/witness',lambda m:witness.add(m.data),profile(20))
events=[];cases=[];err=None
def drive(s,pred,seconds=5.):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        assert child.poll() is None
        rclpy.spin_once(n,timeout_sec=.01);s.tick()
        if pred():return
    raise AssertionError('deadline')
def run(mode,expected,timeout=4.):
    start=time.monotonic();es=[];blocks=[]
    def emit(event,**kw):
        row=dict(case=mode,event=event,steady_s=time.monotonic(),**kw);es.append(row);events.append(row)
    s=ActionSupervisor(c,lambda x:UUID(uuid=list(bytes.fromhex(x))),lambda x:x in witness,emit,blocks.append,timeout=timeout)
    drive(s,s.ready_for_goal);g=PickObject.Goal(object_class=mode);rid=s.send(g)
    assert not s.ready_for_goal()
    if mode=='before_accept':s.request_cancel(rid)
    elif mode in ('cancel','unconfirmed','late'):
        drive(s,lambda:s.rows[rid].accepted_uuid!='');s.request_cancel(rid)
    if mode in ('unconfirmed','late'):
        drive(s,lambda:s.poll(rid)=='FAILED',4.)
        assert s.latched and not s.ready_for_goal() and not s.reset()
        assert not s.rows[rid].resolved
        drive(s,lambda:s.rows[rid].resolved,4.)
        assert s.poll(rid)=='FAILED' and not s.ready_for_goal()
    else:drive(s,lambda:s.poll(rid)==expected,6.)
    a=s.rows[rid];assert s.poll(rid)==expected
    assert sum(x['event']=='GOAL_SENT' for x in es)==1
    if mode!='reject':assert sum(x['event']=='GOAL_ACCEPTED' for x in es)==1 and sum(x['event']=='GOAL_TERMINAL' for x in es)==1 and a.accepted_uuid==a.requested_uuid
    else:assert a.accepted_uuid=='' and a.resolved
    cancel=[x for x in es if x['event']=='CANCEL_REQUEST'];terminal=[x for x in es if x['event']=='GOAL_TERMINAL']
    delta=None
    if cancel and terminal:
        delta=terminal[-1]['steady_s']-cancel[0]['steady_s']
        if mode not in ('unconfirmed','late'):assert delta<=2.
    if mode in ('cancel','before_accept','timeout'):
        assert any(x['event']=='CANCEL_ACK' and x['matches'] for x in es),es
    row=dict(case=mode,result=s.poll(rid),uuid=a.accepted_uuid,terminal=a.terminal_status,cancel_to_terminal_s=delta,blocked=bool(blocks),latched=s.latched,elapsed_s=time.monotonic()-start);cases.append(row);print(json.dumps(row),flush=True)
try:
    for mode,expected,timeout in [('normal','SUCCEEDED_VERIFIED',4.),('reject','REJECTED',4.),('abort','ABORTED',4.),('cancel','CANCELED',4.),('before_accept','CANCELED',4.),('timeout','CANCELED',.2),('late','FAILED',4.),('unconfirmed','FAILED',4.)]:run(mode,expected,timeout)
except BaseException as e:err=repr(e);print(err,flush=True)
finally:
    if child.poll() is None:child.send_signal(signal.SIGINT)
    forced=False
    try:rc=child.wait(timeout=6.)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);rc=child.wait(timeout=3);forced=True
    log.close();n.destroy_node();rclpy.try_shutdown()
    result=dict(result='PASS' if err is None and rc==0 and not forced and len(cases)==8 else 'FAIL',error=err,cases=cases,events=events,process=dict(exit=rc,forced=forced))
    (out/'action-result.json').write_text(json.dumps(result,indent=2)+'\n')
sys.exit(0 if result['result']=='PASS' else 1)
