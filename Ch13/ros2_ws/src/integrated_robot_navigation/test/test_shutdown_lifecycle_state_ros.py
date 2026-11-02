"""Real lifecycle RPCs: rejected activation must not provoke invalid DEACTIVATE.

Protocol fixture only; neither torque-off nor physical stopping is asserted.
"""
import json,time,sys
from pathlib import Path
import pytest
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.lifecycle import LifecycleNode,TransitionCallbackReturn
from rclpy.node import Node
from lifecycle_msgs.srv import GetState,ChangeState
from std_srvs.srv import Trigger
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
import run_navigation_13_5 as runner


@pytest.mark.parametrize('initial',['unconfigured','inactive','active','inconsistent'])
def test_shutdown_checks_actual_state_before_deactivation(initial):
    assert hasattr(runner,'deactivate_crawl_if_active'),'state-aware lifecycle shutdown missing'
    class Owner(LifecycleNode):
        def __init__(self,**kwargs):
            super().__init__('shutdown_lifecycle_owner',**kwargs);self.active=False
            self.create_service(Trigger,'~/report',self.report)
        def on_activate(self,state):
            self.active=True;return TransitionCallbackReturn.SUCCESS
        def on_deactivate(self,state):
            self.active=False;return TransitionCallbackReturn.SUCCESS
        def report(self,request,response):
            response.success=True;response.message=json.dumps(dict(active=self.active));return response
    ctx=Context();rclpy.init(context=ctx)
    owner=Owner(context=ctx);peer=Node('shutdown_state_peer',context=ctx)
    executor=SingleThreadedExecutor(context=ctx);executor.add_node(owner);executor.add_node(peer)
    state=peer.create_client(GetState,'/shutdown_lifecycle_owner/get_state')
    change=peer.create_client(ChangeState,'/shutdown_lifecycle_owner/change_state')
    report=peer.create_client(Trigger,'/shutdown_lifecycle_owner/report')
    calls=[]
    def call(client,request):
        assert client.wait_for_service(timeout_sec=1.)
        calls.append(client.srv_name);future=client.call_async(request);end=time.monotonic()+1.
        while not future.done() and time.monotonic()<end:executor.spin_once(timeout_sec=.005)
        assert future.done(),'actual lifecycle RPC did not return'
        return future.result()
    try:
        if initial!='unconfigured':owner.trigger_configure()
        if initial=='active':owner.trigger_activate()
        if initial=='inconsistent':owner.active=True
        if initial=='inconsistent':
            with pytest.raises(RuntimeError,match='state|active'):
                runner.deactivate_crawl_if_active(call=call,state_client=state,
                    transition_client=change,report_client=report)
            assert change.srv_name not in calls
        else:
            result=runner.deactivate_crawl_if_active(call=call,state_client=state,
                transition_client=change,report_client=report)
            assert result['success'] and not owner.active
            assert result['transition_sent']==(initial=='active')
            assert calls.count(change.srv_name)==int(initial=='active')
            assert result['scope']=='lifecycle_release_not_measured_stop'
            assert 'measured_stop' not in result
        # A subsequent real state service must still work; no executor crash.
        assert call(state,GetState.Request()).current_state.id in (1,2)
    finally:
        executor.shutdown();owner.destroy_node();peer.destroy_node();ctx.try_shutdown()
