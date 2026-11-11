import threading
import time
from types import SimpleNamespace
import numpy as np
from ch13_manipulation_reuse.lease import Lease
from ch13_manipulation_reuse.engine_extension import EngineExtension


def test_revoke_survives_publisher_teardown_before_engine_shutdown():
    extension=EngineExtension.__new__(EngineExtension)
    extension.lease=Lease('engine');extension.lease.phase='REVOKED';extension.lease.message={'state':'REVOKE'}
    extension.node=SimpleNamespace(lock=threading.RLock(),ready_now=lambda:True)
    extension.graph_wall=None;extension.graph={};extension.navigation=None;extension.navigation_receipt=None
    extension.gateway=None;extension.gateway_receipt=None
    extension.rx_wall={}
    extension.goals={};extension.anchor=None;extension.last_phase=None;extension.events=[]
    extension.actions=SimpleNamespace(after=lambda *args:None)
    extension.step(None,SimpleNamespace(mode='ARMED',vx=0.,wz=0.),np.zeros(27),np.zeros(26),
                   {'stamp_ns':1_000_000_000,'yaw':0.},0.)
    assert extension.lease.phase=='REVOKED'
    assert extension.lease.fault==''


def test_gateway_fault_revokes_engine_authority_even_when_platform_holds_zero():
    extension=EngineExtension.__new__(EngineExtension)
    extension.lease=Lease('engine');extension.lease.phase='READY';extension.lease.message={'state':'OFFER'}
    extension.node=SimpleNamespace(lock=threading.RLock(),ready_now=lambda:True)
    extension.graph_wall=time.monotonic();extension.graph={'gateway':1}
    extension.gateway_receipt=time.monotonic();extension.gateway={'mode':'FAULT','fault':'INVALID_STATE:joints'}
    extension.rx_wall={}
    extension.navigation=None;extension.navigation_receipt=None
    extension.goals={};extension.anchor=None;extension.last_phase=None;extension.events=[]
    extension.actions=SimpleNamespace(after=lambda *args:None)
    extension.step(None,SimpleNamespace(mode='ARMED',vx=0.,wz=0.),np.zeros(27),np.zeros(26),
                   {'stamp_ns':1_000_000_000,'yaw':0.},0.)
    assert extension.lease.phase=='FAULT'
    assert extension.lease.fault=='GATEWAY_NOT_HEALTHY'


def test_freshness_clock_is_sampled_after_receipt_lock(monkeypatch):
    extension=EngineExtension.__new__(EngineExtension)
    ticks=[10.]
    class ReceiptLock:
        def __enter__(self):
            ticks[0]=10.001
            extension.navigation_receipt=10.0005
        def __exit__(self,*args):pass
    monkeypatch.setattr(time,'monotonic',lambda:ticks[0])
    extension.lease=Lease('engine');extension.lease.phase='REVOKED'
    observed={}
    def evaluate(clock,now,**kwargs):
        observed.update(now=now,**kwargs)
        return 'REVOKED'
    extension.lease.evaluate=evaluate
    extension.node=SimpleNamespace(lock=ReceiptLock(),ready_now=lambda:True)
    extension.navigation={'phase':'IDLE','output_held':True,'fault':''}
    extension.navigation_receipt=9.99
    extension.gateway_receipt=None;extension.rx_wall={}
    extension.goals={};extension.anchor=None;extension.last_phase=None;extension.events=[]
    extension.actions=SimpleNamespace(after=lambda *args:None)
    extension.step(None,SimpleNamespace(mode='ARMED',vx=0.,wz=0.),np.zeros(27),np.zeros(26),
                   {'stamp_ns':1_000_000_000,'yaw':0.},0.)
    assert observed['navigation_idle']
    assert observed['now']==10.001


def test_diagnostic_spans_preserve_real_monitor_status_and_ownership_counts():
    from ch13_navigation_reuse.callback_timing import CallbackTiming
    from ch13_manipulation_reuse.action_bridge import ActionBridge
    import json
    published=[]
    node=SimpleNamespace(lock=threading.RLock(),callback_timing=CallbackTiming(),count_publishers=lambda topic:1)
    extension=EngineExtension.__new__(EngineExtension);extension.node=node
    extension.lease=Lease('engine');extension.status={'phase':'WAITING','fault':''}
    extension.channels=('mission_lease','manipulation_observation')
    extension.publisher=SimpleNamespace(publish=lambda msg:published.append(json.loads(msg.data)))
    bridge=ActionBridge.__new__(ActionBridge);bridge.node=node;bridge.extension=extension;bridge.feedback=None
    extension.actions=bridge
    extension.monitor()
    assert published==[{'phase':'WAITING','fault':''}]
    assert extension.lease.fault=='' and all(v==1 for v in extension.graph.values())
    spans=node.callback_timing.summary()['rows']
    assert [r['name'] for r in spans]==['action.monitor','manipulation.monitor']
    assert spans[1]['start_wall']<=spans[0]['start_wall']<=spans[0]['end_wall']<=spans[1]['end_wall']
