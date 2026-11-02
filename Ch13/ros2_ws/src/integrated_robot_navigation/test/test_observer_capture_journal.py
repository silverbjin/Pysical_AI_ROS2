"""Capture all original primitive values cheaply; JSON is post-engine work."""
import importlib
import io
import json
import pickle
import struct
from types import SimpleNamespace
import pytest


def codec():return importlib.import_module('observer_journal_13_5')


def test_capture_records_roundtrip_original_values_without_live_json(monkeypatch):
    api=codec()
    rows=[dict(kind='frame',value=dict(capture_ns=706267999997,received_ns=892856332880,
        epoch=0,sequence=i,data=dict(position=(.1,-.2,3.),touching=[True,False],label='실제 촬영')))
        for i in range(600)]
    def forbidden(*args,**kwargs):raise AssertionError('live JSON serialization owns capture callback')
    monkeypatch.setattr(api.json,'dumps',forbidden)
    raw=api.MAGIC+b''.join(api.encode_record(row) for row in rows)
    restored=list(api.read_records(io.BytesIO(raw)))
    assert restored==rows and restored[0]['value']['received_ns']==892856332880


@pytest.mark.parametrize('damage',['magic','length','truncated','global'])
def test_capture_reader_rejects_damage_and_executable_objects(damage):
    api=codec();record=api.encode_record(dict(kind='frame',value=dict(original=9)))
    raw=api.MAGIC+record
    if damage=='magic':raw=b'BADMAGIC'+record
    elif damage=='length':raw=api.MAGIC+struct.pack('>Q',8*1024*1024+1)
    elif damage=='truncated':raw=raw[:-1]
    elif damage=='global':
        payload=pickle.dumps(SimpleNamespace(executable='forbidden'))
        raw=api.MAGIC+struct.pack('>Q',len(payload))+payload
    with pytest.raises((ValueError,RuntimeError,EOFError,pickle.UnpicklingError)):
        list(api.read_records(io.BytesIO(raw)))


def test_probe_capture_avoids_live_json_then_exports_all_original_records(tmp_path,monkeypatch):
    import rclpy
    from rclpy.context import Context
    import probe_navigation_13_5 as probe_api
    import split_observer_13_5 as split
    context=Context();rclpy.init(context=context);probe=None
    try:
        probe=probe_api.NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,
            capture_records=True,context=context)
        with monkeypatch.context() as live:
            def forbidden(*args,**kwargs):raise AssertionError('live JSON in capture path')
            live.setattr(probe_api.json,'dumps',forbidden)
            for index in range(600):
                original=dict(capture_ns=index,received_ns=index+100,values=[.1,.2])
                probe._write('frame',original)
                original['capture_ns']=-1  # enqueue must own immutable bytes
                if index%64==63:probe.flush_log()
        assert not (tmp_path/'observations.jsonl').exists()
        assert (tmp_path/'observations.capture').exists()
        report=split._seal_recording(probe)  # no receiver was started in this fixture
        restored=split._load_recording(tmp_path,report)
        assert len(restored['frames'])==600
        assert restored['frames'][0]['capture_ns']==0 and restored['frames'][-1]['capture_ns']==599
        assert restored['frames'][-1]['received_ns']==699
        rows=[json.loads(line) for line in (tmp_path/'observations.jsonl').read_text().splitlines()]
        assert len(rows)==600 and rows[-1]['value']==restored['frames'][-1]
    finally:
        if probe:probe.close_log();probe.destroy_node()
        context.try_shutdown()


def test_ros_fixed_array_values_remain_equivalent_to_original_json():
    from dataclasses import asdict
    from integrated_robot_interfaces.msg import FootContacts
    from integrated_robot_navigation.observations import sensor_sample
    message=FootContacts();message.header.frame_id='odom'
    message.names=['fr_foot','fl_foot','rr_foot','rl_foot']
    row=dict(kind='contacts',value=asdict(sensor_sample('contacts',message,123,0)))
    expected=json.loads(json.dumps(row,allow_nan=False))
    raw=codec().MAGIC+codec().encode_record(row)
    restored=next(codec().read_records(io.BytesIO(raw)))
    assert json.loads(json.dumps(restored,allow_nan=False))==expected


def test_cyclic_capture_rejects_without_unbounded_validation():
    import signal
    cyclic=[];cyclic.append(cyclic)
    def deadline(*args):raise TimeoutError('cyclic capture validation did not terminate')
    previous=signal.signal(signal.SIGALRM,deadline)
    try:
        signal.setitimer(signal.ITIMER_REAL,.2)
        with pytest.raises(ValueError,match='cycl'):
            payload=codec().encode_record(dict(kind='frame',value=cyclic))
            list(codec().read_records(io.BytesIO(codec().MAGIC+payload)))
    finally:
        signal.setitimer(signal.ITIMER_REAL,0.)
        signal.signal(signal.SIGALRM,previous)


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-float('inf')])
def test_invalid_numeric_evidence_never_enters_restored_history(value):
    api=codec()
    with pytest.raises(ValueError,match='finite'):
        payload=api.encode_record(dict(kind='frame',value=dict(measured=value)))
        list(api.read_records(io.BytesIO(api.MAGIC+payload)))
