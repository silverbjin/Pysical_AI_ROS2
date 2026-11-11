"""Educational performance targets do not turn incomplete motion into success."""
import copy
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

from ch13_system_validation.metrics import assess_trials


def rows():
    return [dict(uuid=str(i), complete=True, success=True, sim_s=400., wall_s=900.,
                 position_error_m=.08, max_tilt_rad=.12, cpu_percent=80.) for i in range(10)]


def test_educational_thresholds_are_explicit_and_original_targets_remain_strict():
    samples = rows()
    assert assess_trials(samples)['result'] == 'FAIL'
    result = assess_trials(samples, criteria_profile='education_v1')
    assert result['result'] == 'PASS'
    assert result['criteria']['profile'] == 'education_v1'
    assert result['criteria']['mean_sim_s_max'] == 600.
    assert result['mean_sim_s'] == 400.


def test_eighty_percent_keeps_failures_in_denominator_without_rewarding_early_abort():
    samples = rows()
    for row in samples[:2]:
        row.update(success=False, sim_s=1., wall_s=2., position_error_m=None)
    result = assess_trials(samples, criteria_profile='education_v1')
    assert result['result'] == 'PASS'
    assert result['success_rate'] == .8
    assert result['mean_sim_s'] == 400.
    assert result['mean_wall_s'] == 900.
    assert result['metric_counts']['successful'] == 8
    samples[2]['success'] = False
    assert assess_trials(samples, criteria_profile='education_v1')['result'] == 'FAIL'


@pytest.mark.parametrize('field,value', [('sim_s', 600.01), ('position_error_m', .1),
    ('max_tilt_rad', .15), ('cpu_percent', 85.)])
def test_relaxed_boundaries_are_still_enforced(field, value):
    samples = rows()
    for row in samples:
        row[field] = value
    assert assess_trials(samples, criteria_profile='education_v1')['result'] == 'FAIL'


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'unfinished', 'nan',
    'negative', 'successful_missing', 'failed_nan', 'no_success'])
def test_relaxed_policy_rejects_incomplete_or_corrupt_evidence(mutation):
    samples = rows()
    if mutation == 'missing': samples.pop()
    if mutation == 'duplicate': samples[1]['uuid'] = samples[0]['uuid']
    if mutation == 'unfinished': samples[0]['complete'] = False
    if mutation == 'nan': samples[0]['cpu_percent'] = math.nan
    if mutation == 'negative': samples[0]['sim_s'] = -1.
    if mutation == 'successful_missing': samples[0]['position_error_m'] = None
    if mutation == 'failed_nan': samples[0].update(success=False, cpu_percent=math.nan)
    if mutation == 'no_success':
        for row in samples: row['success'] = False
    assert assess_trials(samples, criteria_profile='education_v1')['result'] == 'FAIL'


def test_failed_attempt_measurements_still_contribute_to_tilt_and_cpu():
    samples = rows()
    samples[0].update(success=False, position_error_m=None, max_tilt_rad=.16)
    assert assess_trials(samples, criteria_profile='education_v1')['result'] == 'FAIL'
    samples[0].update(max_tilt_rad=.1, cpu_percent=200.)
    assert assess_trials(samples, criteria_profile='education_v1')['result'] == 'FAIL'


def test_unknown_profile_is_rejected_instead_of_silently_using_relaxed_policy():
    with pytest.raises(ValueError):
        assess_trials(rows(), criteria_profile='typo')


def test_new_batch_freezes_criteria_and_refuses_policy_or_physics_substitution():
    from ch13_system_validation.batch import make_plan, assess_batch
    plan = make_plan('a'*64, {'level2_obstacles':'b'*64, 'level3_house':'c'*64},
                     criteria_profile='education_v1')
    assert plan['schema'] == 'ch13_level23_ten_v2'
    samples = [dict(row, uuid=slot['uuid'], scenario=slot['scenario'],
        scenario_sha256=slot['scenario_sha256'], source_manifest_sha256='a'*64,
        profile='actual', criteria_profile='education_v1', criteria=copy.deepcopy(plan['criteria']),
        physical={name:{'result':'PASS'} for name in ('world','pick','transport')})
        for slot,row in zip(plan['slots'],rows())]
    assert assess_batch(plan, samples)['result'] == 'PASS'
    samples[0]['criteria_profile'] = 'book_v1'
    assert assess_batch(plan, samples)['result'] == 'FAIL'
    samples[0]['criteria_profile'] = 'education_v1'
    samples[0]['physical']['transport']['result'] = 'FAIL'
    assert assess_batch(plan, samples)['result'] == 'FAIL'
    changed = copy.deepcopy(plan)
    changed['criteria']['mean_sim_s_max'] = 10000.
    with pytest.raises(ValueError): assess_batch(changed, samples)


@pytest.mark.parametrize('script', ['run_mission.py', 'evaluate_batch.py'])
def test_student_cli_exposes_named_performance_policy_before_starting_engine(script):
    path = Path(__file__).resolve().parents[4]/'scripts/reuse_13_8'/script
    # pytest's in-process source paths are not inherited by a child. Test the
    # immutable snapshot, not the previous installed package in the overlay.
    package = str(Path(__file__).resolve().parents[1])
    environment = dict(os.environ, PYTHONPATH=package+os.pathsep+os.environ.get('PYTHONPATH', ''))
    result = subprocess.run([sys.executable, str(path), '--help'], text=True,
                            capture_output=True, timeout=20., env=environment)
    assert result.returncode == 0, result.stderr
    assert '--criteria-profile' in result.stdout
    assert 'education_v1' in result.stdout and 'book_v1' in result.stdout
