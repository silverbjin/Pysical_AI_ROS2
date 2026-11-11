"""Diagnostic wrappers must preserve callbacks and bound memory."""
import pytest
from ch13_navigation_reuse.callback_timing import CallbackTiming, timed_callback

class Subject:
    def __init__(self, trace):self.callback_timing=trace
    @timed_callback('sample')
    def callback(self, value, *, fail=False):
        if fail:raise ValueError('original failure')
        return value

def test_callback_trace_preserves_return_exception_and_bounds():
    trace=CallbackTiming(limit=2);subject=Subject(trace)
    assert subject.callback(7)==7
    with pytest.raises(ValueError,match='original failure'):subject.callback(0,fail=True)
    assert subject.callback(9)==9
    report=trace.summary()
    assert report['total']==3 and len(report['rows'])==2
    for row in report['rows']:
        assert row['name']=='sample' and row['end_wall']>=row['start_wall']
        assert row['cpu_s']>=0 and row['thread_id']>0
    assert report['rows'][0]['raised'] is True
    assert report['rows'][1]['raised'] is False

def test_disabled_callback_trace_does_not_read_clock(monkeypatch):
    def forbidden():raise AssertionError('disabled tracing must not sample clocks')
    monkeypatch.setattr('ch13_navigation_reuse.callback_timing.time.monotonic',forbidden)
    assert Subject(None).callback('unchanged')=='unchanged'
