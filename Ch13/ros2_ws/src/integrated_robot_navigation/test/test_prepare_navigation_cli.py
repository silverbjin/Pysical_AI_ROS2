"""Breaks caught: deploying an offline profile or overwriting an existing result."""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_prepare_cli_creates_offline_profile_and_refuses_overwrite(tmp_path):
    src = Path(__file__).resolve().parents[2]
    chapter = src.parents[1]
    environment = dict(os.environ)
    environment['PYTHONPATH'] = os.pathsep.join(
        [str(src/'integrated_robot_navigation'), str(src/'integrated_robot_vision'),
         environment.get('PYTHONPATH', '')])
    output = tmp_path/'offline-profile'
    command = [sys.executable, str(chapter/'scripts/prepare_navigation_model_13_5.py'),
               '--output-dir', str(output)]
    result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    profile = json.loads((output/'carry_profile.json').read_text())
    assert profile['state'] == 'offline' and profile['native_evidence'] == {}
    assert profile['limits']['hip_mount_y_m'] == .13
    original = (output/'carry_profile.json').read_bytes()
    repeat = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=60)
    assert repeat.returncode != 0
    assert (output/'carry_profile.json').read_bytes() == original
