"""The command must execute real episodes and reject meaningless run lengths."""
import json

import pytest

from quadruped_rl.demo import main


@pytest.mark.parametrize('policy', ['random', 'stand'])
def test_demo_runs_and_saves_finite_summary(tmp_path, policy, capsys):
    output = tmp_path / 'nested' / 'summary.json'
    assert main(['--steps', '120', '--policy', policy, '--observation-mode', 'full',
                 '--output', str(output)]) == 0
    report = json.loads(output.read_text())
    assert report['steps'] == 120
    assert report['physics_seconds'] == pytest.approx(1.2)
    assert report['observation_size'] == 45
    assert report['policy'] == policy
    assert json.loads(capsys.readouterr().out) == report


@pytest.mark.parametrize('args', [['--steps', '0'], ['--steps', '-1'],
    ['--target-velocity', 'nan'], ['--target-velocity', 'inf']])
def test_demo_rejects_invalid_config(args):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
