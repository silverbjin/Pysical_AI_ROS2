"""Large diagnostic JSON must not be re-encoded while ROS ingestion is live."""
import json
from types import SimpleNamespace
import pytest
import run_navigation_13_5 as runner


def payload():
    row=dict(ctrl=[.5],joint_velocity=[0.],steady_ns=123,snapshot_ros_ns=99)
    return dict(schema=1,frozen=True,joints=['fixture_joint'],
        cm_write=dict(rows=[row]),pre_step=dict(rows=[row]))


def test_native_stop_preserves_raw_reply_and_requires_both_actual_worker_joins(tmp_path):
    assert hasattr(runner,'capture_native_worker_stop'),'worker stop reply evidence missing'
    value=dict(sensor_worker_joined=True,applied_worker_joined=True,engine_exit_acknowledgment=False,
        applied_submitted=10,applied_published=9,applied_overwritten=1,applied_dropped_busy=0)
    text=json.dumps(value,separators=(',',':'));path=tmp_path/'stop.json'
    assert runner.capture_native_worker_stop(SimpleNamespace(success=True,message=text),path)
    assert path.read_text()==text
    with pytest.raises(FileExistsError):
        runner.capture_native_worker_stop(SimpleNamespace(success=True,message=text),path)
    for key in ('sensor_worker_joined','applied_worker_joined'):
        bad={**value,key:False};target=tmp_path/(key+'.json')
        assert runner.capture_native_worker_stop(SimpleNamespace(success=True,message=json.dumps(bad)),target) is False


@pytest.mark.parametrize('damage',['old_string','engine_ack','incomplete_count','negative','server_failed'])
def test_server_ack_or_incomplete_worker_reply_never_proves_normal_stop(tmp_path,damage):
    assert hasattr(runner,'capture_native_worker_stop'),'worker stop reply evidence missing'
    value=dict(sensor_worker_joined=True,applied_worker_joined=True,engine_exit_acknowledgment=False,
        applied_submitted=10,applied_published=10,applied_overwritten=0,applied_dropped_busy=0)
    if damage=='engine_ack':value['engine_exit_acknowledgment']=True
    if damage=='incomplete_count':value['applied_published']=9
    if damage=='negative':value['applied_dropped_busy']=-1
    text='service ACK only' if damage=='old_string' else json.dumps(value)
    path=tmp_path/'raw_stop.json'
    assert runner.capture_native_worker_stop(SimpleNamespace(success=damage!='server_failed',message=text),path) is False
    assert path.read_text()==text


def test_trace_capture_preserves_server_json_without_live_decode_or_encode(tmp_path,monkeypatch):
    assert hasattr(runner,'capture_native_command_trace'),'live trace copy boundary missing'
    text=json.dumps(payload(),separators=(',',':'));target=tmp_path/'trace.json';calls=[]
    def call(client,request,*,seconds):
        calls.append((client,seconds));return SimpleNamespace(success=True,message=text)
    def forbidden(*args,**kwargs):raise AssertionError('JSON conversion while callbacks are live')
    with monkeypatch.context() as patch:
        patch.setattr(runner.json,'loads',forbidden);patch.setattr(runner.json,'dumps',forbidden)
        assert runner.capture_native_command_trace('mujoco',call=call,client='owned',path=target)
    assert target.read_text()==text and calls==[('owned',10.)]
    with pytest.raises(FileExistsError):
        runner.capture_native_command_trace('mujoco',call=call,client='owned',path=target)
    assert target.read_text()==text


def test_gazebo_stop_never_waits_for_the_mujoco_only_trace_service(tmp_path):
    assert hasattr(runner,'capture_native_command_trace'),'engine-scoped trace boundary missing'
    def forbidden(*args,**kwargs):raise AssertionError('Gazebo requested a MuJoCo-only service')
    target=tmp_path/'trace.json'
    assert runner.capture_native_command_trace('gazebo',call=forbidden,client=None,path=target) is False
    assert not target.exists()


@pytest.mark.parametrize('damage',['json','schema','unfrozen','empty','shape','nonfinite'])
def test_bad_trace_is_still_rejected_after_actual_resource_join(tmp_path,damage):
    assert hasattr(runner,'validate_native_command_trace'),'post-join validation missing'
    value=payload()
    if damage=='schema':value['schema']=0
    elif damage=='unfrozen':value['frozen']=False
    elif damage=='empty':value['pre_step']['rows']=[]
    elif damage=='shape':value['pre_step']['rows'][0]['ctrl']=[]
    elif damage=='nonfinite':value['pre_step']['rows'][0]['ctrl']=[float('inf')]
    target=tmp_path/'trace.json';target.write_text('{broken' if damage=='json' else json.dumps(value))
    with pytest.raises((ValueError,RuntimeError)):
        runner.validate_native_command_trace(target,parent_reaped=True,receivers_joined=True)


def test_trace_validation_requires_reap_and_all_receiver_joins(tmp_path):
    assert hasattr(runner,'validate_native_command_trace'),'post-join validation missing'
    target=tmp_path/'trace.json';target.write_text(json.dumps(payload()))
    for reaped,joined in ((False,False),(False,True),(True,False)):
        with pytest.raises(RuntimeError,match='join|reap'):
            runner.validate_native_command_trace(target,parent_reaped=reaped,receivers_joined=joined)
    report=runner.validate_native_command_trace(target,parent_reaped=True,receivers_joined=True)
    assert report['passed'] is True and report['rows']==dict(cm_write=1,pre_step=1)
