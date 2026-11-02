"""Full history belongs after the ROS process join, never inside its deadline."""
from collections import Counter,deque
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
import split_observer_13_5 as module


def test_worker_closes_ros_without_decoding_or_pickling_full_history(tmp_path,monkeypatch):
    import rclpy
    events=[]
    class Probe:
        def __init__(self,directory,**kwargs):
            self.journal_path=Path(directory)/'observations.jsonl'
            self.journal_path.write_text(json.dumps(dict(kind='frame',value={'original':7}))+'\n')
            self.journal_counts=Counter(frame=1)
            self.frames=deque([{'original':7}],maxlen=128)
            self.native_controls=[];self.transforms=[];self.body_references=[]
            self.errors=[];self.transport_errors=[];self.tf_api={};self.gc_spans=[]
            self.journal=SimpleNamespace(report=lambda:dict(joined=True,error=None,submitted=1,written=1))
        def fault(self):return None
        def restore_history(self,**kwargs):
            raise AssertionError('whole history decoded inside process join budget')
        def close_log(self):events.append('journal_closed')
        def timing_snapshot(self):return {}
        def destroy_node(self):events.append('ros_destroyed')
    class Receiver:
        def __init__(self,node):pass
        def check(self):pass
        def shutdown(self,**kwargs):events.append('receiver_joined');return True
        def report(self):return dict(closed=True)
    class Connection:
        def send(self,value):pass
        def poll(self,*args):return True
        def recv(self):return ('stop',None)
        def close(self):events.append('ipc_closed')
    monkeypatch.setattr(module,'NavigationProbe',Probe)
    monkeypatch.setattr(module,'ProbeReceiver',Receiver)
    monkeypatch.setattr(module,'_modules',lambda:{})
    monkeypatch.setattr(module.os,'setsid',lambda:None)
    monkeypatch.setattr(rclpy,'init',lambda **kwargs:None)
    monkeypatch.setattr(rclpy,'ok',lambda:True)
    monkeypatch.setattr(rclpy,'try_shutdown',lambda:events.append('context_closed'))
    module._observe(str(tmp_path),'gazebo',Connection())
    assert events.index('receiver_joined')<events.index('journal_closed')<events.index('ros_destroyed')
    assert events.index('ros_destroyed')<events.index('context_closed')<events.index('ipc_closed')
    assert not (tmp_path/'observer_snapshot.pickle').exists()
    report=json.loads((tmp_path/'observer_process_report.json').read_text())
    assert report['failure'] is None and report['ros_closed'] is True
    values=module._load_recording(tmp_path,report['recording'])
    assert values['frames']==[{'original':7}]


@pytest.mark.parametrize('damage',['none','truncated','missing','count','hash','foreign_path'])
def test_full_journal_validation_preserves_every_record_and_rejects_damage(tmp_path,damage):
    root=tmp_path/'full';root.mkdir();path=root/'observations.jsonl'
    rows=[dict(kind='frame',value=dict(original=i,stamp_ns=i*2)) for i in range(600)]
    rows.insert(0,dict(kind='sensor',value=dict(original_receipt=123)))
    path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    report=dict(journal_path='observations.jsonl',journal_size=path.stat().st_size,
        journal_sha256=module._digest(path),counts={'frame':600},records=601,
        errors=[],transport_errors=[],tf_api={})
    if damage=='truncated':path.write_text(path.read_text()+'{broken')
    elif damage=='missing':path.write_text('')
    elif damage=='count':report['counts']['frame']=599
    elif damage=='hash':report['journal_sha256']='0'*64
    elif damage=='foreign_path':report['journal_path']='../outside.jsonl'
    if damage!='none':
        with pytest.raises((RuntimeError,ValueError)):
            module._load_recording(root,report)
    else:
        values=module._load_recording(root,report)
        assert len(values['frames'])==600 and values['frames'][0]['original']==0
        assert values['frames'][-1]['stamp_ns']==1198
        assert module._load_recording(root,report,retain=False) is None
