"""Exercise the real warmup caller against a slow, successful action result."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest


@pytest.mark.parametrize('profile,finishes',[('carry_v1',True),('',False)])
def test_continuous_warmup_waits_for_measured_result_without_changing_the_goal(monkeypatch,tmp_path,profile,finishes):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE',profile)
    source=Path(__file__).resolve().parents[5]/'Ch13/scripts/reuse_13_6/run_arm_probe.py'
    spec=importlib.util.spec_from_file_location('warmup_under_test',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    wall=[0.];values={**{f'joint{i}':0. for i in range(1,9)},'joint5':.02}
    clients=[];arm_goals=[]
    class Future:
        def __init__(self,value,ready=0.):self.value=value;self.ready=ready
        def done(self):return wall[0]>=self.ready
        def result(self):return self.value
    class Client:
        def __init__(self,node,typ,name):self.name=name;self.destroyed=False;clients.append(self)
        def server_is_ready(self):return True
        def send_goal_async(self,goal):
            if self.name==module.ARM:
                arm_goals.append(goal)
                terminal=SimpleNamespace(status=4,result=SimpleNamespace(error_code=0,error_string='measured'))
                result=Future(terminal,25.)
            else:
                values['joint7']=goal.command.position;values['joint8']=-goal.command.position
                result=Future(SimpleNamespace(status=4,result=SimpleNamespace(reached_goal=True,stalled=False,effort=0.)))
            handle=SimpleNamespace(accepted=True,get_result_async=lambda:result)
            return Future(handle)
        def destroy(self):self.destroyed=True
    def until(predicate,seconds):
        end=wall[0]+seconds
        while wall[0]<=end:
            if predicate():return True
            wall[0]+=1.
        return False
    def snapshot():
        return dict(joints=SimpleNamespace(name=list(values),position=list(values.values())),
                    platform=dict(stationary_ready=True),clock_ns=int(wall[0]/5*1e9))
    def work():
        module.work(node=None,until=until,snapshot=snapshot,status=lambda:{},control={},
                    case='normal',out=tmp_path,action_client_factory=Client)
    if finishes:
        work();assert wall[0]==25.
    else:
        with pytest.raises(AssertionError,match='measured arm terminal deadline'):work()
        assert wall[0]==21.
    assert len(arm_goals)==1
    assert [p.time_from_start.sec for p in arm_goals[0].trajectory.points]==[0,2,4]
    assert all(c.destroyed for c in clients)
