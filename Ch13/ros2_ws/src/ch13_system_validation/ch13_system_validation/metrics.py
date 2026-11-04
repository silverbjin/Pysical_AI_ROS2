"""Fail-closed textbook metrics with an explicit attempt denominator."""
import math
from statistics import mean

FIELDS=('sim_s','wall_s','position_error_m','max_tilt_rad','cpu_percent')


def assess_trials(trials, expected=10):
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
