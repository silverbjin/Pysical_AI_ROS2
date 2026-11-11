"""Fail-closed textbook metrics with an explicit attempt denominator."""
import math
from statistics import mean
from .criteria import get_criteria

FIELDS=('sim_s','wall_s','position_error_m','max_tilt_rad','cpu_percent')


def _assess_book(trials, expected=10):
    if type(expected) is not int or expected<1:raise ValueError('positive expected attempt count required')
    ids=[r.get('uuid') for r in trials]
    valid=all(isinstance(r.get(k),(int,float)) and not isinstance(r.get(k),bool)
              and math.isfinite(r[k]) and r[k]>=0 for r in trials for k in FIELDS)
    complete=all(r.get('complete') is True and type(r.get('success')) is bool for r in trials)
    unique=all(isinstance(i,str) and i for i in ids) and len(set(ids))==len(ids)
    rate=sum(r.get('success') is True and r.get('complete') is True for r in trials)/max(expected,len(trials))
    values={k:mean(r[k] for r in trials) if valid and trials else None for k in FIELDS}
    checks=dict(attempt_count=len(trials)==expected,unique_attempts=unique,complete=complete,
                finite_nonnegative_metrics=valid,success_rate=rate>=.9,
                mean_mission_sim_s=values['sim_s'] is not None and values['sim_s']<=120.,
                position_error=bool(valid and trials) and max(r['position_error_m'] for r in trials)<.03,
                maximum_tilt=bool(valid and trials) and max(r['max_tilt_rad'] for r in trials)<.1,
                mean_cpu=values['cpu_percent'] is not None and values['cpu_percent']<70.)
    return dict(result='PASS' if all(checks.values()) else 'FAIL',checks=checks,
                attempts=len(trials),expected=expected,success_rate=rate,
                mean_sim_s=values['sim_s'],mean_wall_s=values['wall_s'],
                mean_cpu_percent=values['cpu_percent'],time_target_basis='simulation_Start_to_Finish')


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def assess_trials(trials, expected=10, *, criteria_profile='book_v1'):
    criteria = get_criteria(criteria_profile)
    if criteria.profile == 'book_v1':
        result = _assess_book(trials, expected)
        result['criteria'] = criteria.record()
        result['metric_population'] = 'all_attempts_require_all_metrics'
        return result
    if type(expected) is not int or expected < 1:
        raise ValueError('positive expected attempt count required')
    ids = [r.get('uuid') for r in trials]
    successful = [r for r in trials if r.get('success') is True and r.get('complete') is True]
    # Closed failures stay in the denominator. Their unavailable measurements
    # remain null; any supplied corrupt value still invalidates the evidence.
    valid = all(_finite(r.get(k)) for r in successful for k in FIELDS)
    valid = valid and all(r.get(k) is None or _finite(r[k]) for r in trials for k in FIELDS)
    complete = all(r.get('complete') is True and type(r.get('success')) is bool for r in trials)
    unique = all(isinstance(i, str) and i for i in ids) and len(set(ids)) == len(ids)
    rate = len(successful)/max(expected, len(trials))
    sim = mean(r['sim_s'] for r in successful) if valid and successful else None
    wall = mean(r['wall_s'] for r in successful) if valid and successful else None
    cpu = [r['cpu_percent'] for r in trials if _finite(r.get('cpu_percent'))]
    tilts = [r['max_tilt_rad'] for r in trials if _finite(r.get('max_tilt_rad'))]
    average_cpu = mean(cpu) if valid and cpu else None
    checks = dict(attempt_count=len(trials) == expected, unique_attempts=unique,
        complete=complete, finite_nonnegative_metrics=valid,
        success_rate=rate >= criteria.success_rate_min,
        mean_mission_sim_s=sim is not None and sim <= criteria.mean_sim_s_max,
        position_error=bool(valid and successful) and
            max(r['position_error_m'] for r in successful) < criteria.position_error_m_max,
        maximum_tilt=bool(valid and tilts) and max(tilts) < criteria.maximum_tilt_rad,
        mean_cpu=average_cpu is not None and average_cpu < criteria.mean_cpu_percent_max)
    return dict(result='PASS' if all(checks.values()) else 'FAIL', checks=checks,
        attempts=len(trials), expected=expected, success_rate=rate,
        mean_sim_s=sim, mean_wall_s=wall, mean_cpu_percent=average_cpu,
        time_target_basis='simulation_Start_to_Finish', criteria=criteria.record(),
        metric_population='successful_duration_position; all_available_cpu_tilt',
        metric_counts=dict(successful=len(successful), cpu=len(cpu), tilt=len(tilts)))
