"""Owned diagnostic prefix cannot profile engines or become G1 acceptance."""
from pathlib import Path
import shlex
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
import run_navigation_13_5 as runner


def test_profile_default_has_no_prefix_and_explicit_target_is_one_owned_node(tmp_path):
    assert runner.g1_profile_arguments(None,tmp_path)==[]
    args=runner.g1_profile_arguments('motion_guard',tmp_path)
    assert args[0]=='launch-prefix:='+shlex.join([sys.executable,'-m','cProfile','-o',str(tmp_path/'motion_guard.prof')])
    assert args[1]=='launch-prefix-filter:=^motion_guard$'
    with pytest.raises(ValueError):runner.g1_profile_arguments('gz',tmp_path)
    (tmp_path/'motion_guard.prof').touch()
    with pytest.raises(ValueError):runner.g1_profile_arguments('motion_guard',tmp_path)


def test_profiled_diagnostic_preserves_every_check_but_cannot_pass_acceptance():
    base=runner.native_required_checks('relay100','allowance50um','gazebo')
    diagnostic=runner.native_required_checks('relay100','allowance50um','gazebo',profile_node='motion_guard')
    assert base<diagnostic and diagnostic-base=={'unprofiled_acceptance'}
