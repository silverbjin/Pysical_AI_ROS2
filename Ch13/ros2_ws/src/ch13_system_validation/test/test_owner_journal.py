"""Exercise the real handoff lifecycle without a robot or DDS endpoint."""
import gc
import json
from contextlib import nullcontext
from pathlib import Path

import pytest


@pytest.mark.parametrize('profile,pretty', [('carry_v1', False), ('carry_v1', True), ('', False)])
@pytest.mark.parametrize('work_fails', [False, True])
def test_owner_status_journal_and_gc_probe_follow_live_handoff(tmp_path, monkeypatch, profile, pretty, work_fails):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[4]/'scripts/reuse_13_6'))
    monkeypatch.setenv('CH13_VALIDATION_PROFILE', profile)
    from run_handoff import handoff
    from std_msgs.msg import String

    raw_rows = []
    class Node:
        phase = 'WAITING'
        timer = None
        destroyed = []
        def create_subscription(self, kind, name, callback, depth):
            self.callback = callback
            return 'subscription'
        def create_publisher(self, *args):
            return self
        def publish(self, message):
            self.phase = 'REVOKED' if json.loads(message.data)['state'] == 'REVOKE' else 'READY'
        def create_timer(self, period, callback, **kwargs):
            self.timer = callback
            return 'timer'
        def destroy_timer(self, handle): self.destroyed.append(handle)
        def destroy_subscription(self, handle): self.destroyed.append(handle)
        def destroy_publisher(self, handle): self.destroyed.append('publisher')
        def emit(self):
            value = dict(session='unit-session', phase=self.phase, nested={'values': [1, 2]})
            raw = json.dumps(value, indent=2) if pretty else json.dumps(value, separators=(',', ':'))
            raw_rows.append(raw)
            self.callback(String(data=raw))
    node = Node()
    def until(predicate, timeout):
        for _ in range(4):
            if node.timer: node.timer()
            node.emit()
            if predicate(): return True
        return False
    before = list(gc.callbacks)
    enabled = gc.isenabled()
    def work(**context):
        gc.collect(2)
        assert context['status']()['phase'] == 'READY'
        if work_fails: raise RuntimeError('injected work failure')
    with pytest.raises(RuntimeError, match='injected work failure') if work_fails else nullcontext():
        result = handoff(node=node, until=until, call=None, out=tmp_path, goal_id='unit-goal',
                         target=[0, 0], snapshot=lambda:dict(clock_ns=123, observation={'capture_ns': 123}),
                         case='pick', work=work)
        assert result['final_status']['phase'] == 'REVOKED'
        assert result['live_status_samples'] == len(raw_rows)
    lines = (tmp_path/'manipulation_status.jsonl').read_text().splitlines()
    assert [json.loads(line) for line in lines] == [json.loads(raw) for raw in raw_rows]
    assert node.destroyed == ['timer', 'subscription', 'publisher']
    assert list(gc.callbacks) == before and gc.isenabled() == enabled
    if profile == 'carry_v1':
        if not pretty: assert lines == raw_rows
        probe = json.loads((tmp_path/'owner_gc_timing.json').read_text())
        assert probe['policy_changed'] is False
        assert probe['counts']['2'] >= 1
    else:
        assert not (tmp_path/'owner_gc_timing.json').exists()
