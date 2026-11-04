"""Advisory filesystem delivery must never become robot cancellation authority."""
import json
import threading
from ch13_system_validation.telemetry import LiveStatusWriter


def test_reader_lock_error_is_recorded_and_next_snapshot_can_be_published(tmp_path):
    attempted=threading.Event();successful=threading.Event();seen=[]
    def emit(value):
        seen.append(value['sequence'])
        if value['sequence']==1:
            attempted.set();raise PermissionError('Windows reader denies rename')
        successful.set()
    writer=LiveStatusWriter(tmp_path/'status.json',emit=emit)
    try:
        writer.offer({'sequence':1});assert attempted.wait(2.)
        writer.offer({'sequence':2});assert successful.wait(2.)
    finally:report=writer.close()
    assert report['joined'] and report['write_errors']==1 and report['published']==1
    assert 'PermissionError' in report['last_error'] and seen==[1,2]


def test_blocked_writer_has_one_waiting_slot_and_cannot_block_the_ros_owner(tmp_path):
    entered=threading.Event();release=threading.Event();seen=[]
    def emit(value):
        if value['sequence']==1:entered.set();release.wait()
        seen.append(value['sequence'])
    writer=LiveStatusWriter(tmp_path/'status.json',emit=emit)
    try:
        writer.offer({'sequence':1});assert entered.wait(2.)
        writer.offer({'sequence':2});writer.offer({'sequence':3})
        assert seen==[]
        assert writer.close(timeout=.01)['joined'] is False
    finally:
        release.set();report=writer.close()
    assert report['joined'] and report['overwritten_waiting']==1 and seen==[1,3]


def test_final_snapshot_is_written_atomically_and_owned_thread_joins(tmp_path):
    path=tmp_path/'status.json';writer=LiveStatusWriter(path)
    writer.offer({'sequence':7,'scope':'advisory'})
    report=writer.close()
    assert report['joined'] and report['write_errors']==0
    assert json.loads(path.read_text())=={'sequence':7,'scope':'advisory'}
    assert not path.with_suffix('.tmp').exists()
