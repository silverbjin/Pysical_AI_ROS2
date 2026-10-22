"""Stop is allowed after observed pause, never from a pause RPC ACK alone."""
import importlib
import json
import subprocess
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('paused', [False, True])
def test_quiescence_requires_observed_world_pause(monkeypatch, paused):
    runner = importlib.import_module('run_vision_13_4')
    calls = []
    def execute(command, **kwargs):
        calls.append(command)
        assert kwargs['timeout'] <= 5
        if command[:2] == ['gz', 'service']:
            assert command[command.index('--req')+1] == 'pause: true'
            return SimpleNamespace(returncode=0, stdout='data: true\n', stderr='')
        assert command[:2] == ['gz', 'topic']
        return SimpleNamespace(returncode=0, stdout=json.dumps({'paused': paused}), stderr='')
    monkeypatch.setattr(runner.subprocess, 'run', execute)
    record = runner.quiesce_gazebo('section_13_4')
    assert record['confirmed'] is paused
    assert len(calls) == 2


def test_pause_failure_does_not_claim_quiescence(monkeypatch):
    runner = importlib.import_module('run_vision_13_4')
    def execute(command, **kwargs):
        assert command[:2] == ['gz', 'service']
        raise subprocess.TimeoutExpired(command, kwargs['timeout'])
    monkeypatch.setattr(runner.subprocess, 'run', execute)
    record = runner.quiesce_gazebo('section_13_4')
    assert record['confirmed'] is False and record['error']
