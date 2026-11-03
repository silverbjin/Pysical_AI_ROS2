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
    extension.navigation=None;extension.navigation_receipt=None
    extension.goals={};extension.anchor=None;extension.last_phase=None;extension.events=[]
    extension.actions=SimpleNamespace(after=lambda *args:None)
    extension.step(None,SimpleNamespace(mode='ARMED',vx=0.,wz=0.),np.zeros(27),np.zeros(26),
                   {'stamp_ns':1_000_000_000,'yaw':0.},0.)
    assert extension.lease.phase=='FAULT'
    assert extension.lease.fault=='GATEWAY_NOT_HEALTHY'
