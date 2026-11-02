"""Audit the exact hashed sources without walking historical engine evidence."""
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]/'scripts'))
import run_navigation_13_5 as runner


def test_git_identity_keeps_dirty_and_untracked_runtime_files_not_evidence(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    source = tmp_path/'source.py'
    source.write_text('old\n')
    subprocess.run(['git', 'add', 'source.py'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '-qm', 'fixture'], cwd=tmp_path, check=True)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=tmp_path, text=True).strip()
    source.write_text('changed\n')
    (tmp_path/'new.py').write_text('new\n')
    (tmp_path/'evidence').mkdir()
    (tmp_path/'evidence/old-run.log').write_text('not executable runtime source\n')
    result = runner.runtime_git_identity(tmp_path, ['source.py', 'new.py'])
    assert result['head'] == head
    assert result['dirty_scope'] == 'hashed_runtime_files_only'
    assert ' M source.py' in result['dirty'] and '?? new.py' in result['dirty']
    assert 'evidence' not in result['dirty']


def test_empty_scope_cannot_fall_back_to_full_repository_walk(tmp_path):
    with pytest.raises(ValueError, match='runtime source scope'):
        runner.runtime_git_identity(tmp_path, [])
