"""Replan the native 46921c07 geometry; never claim it is a new physical trial."""
import json
from pathlib import Path
import numpy as np
import pytest
from gait_fixture import IdealFeedback
from test_gait import machine
from integrated_robot_navigation.projection import body_rotation
from integrated_robot_navigation.support import center_of_mass,support_margin


def test_absolute_virtual_com_cannot_grant_zero_shift_when_measured_support_is_unsafe(nav_robot_model):
    row=json.loads(Path(__file__).with_name('native_4692_support.json').read_text())
    value=machine(nav_robot_model,IdealFeedback(nav_robot_model))
    value.state='CRAWL';value.reference_body=np.array(row['reference_body'])
    value._targets={name:np.array(point) for name,point in row['targets'].items()}
    value._index=value.ORDER.index(row['swing_foot'])
    q=row['joints']['position'];body=np.eye(4)
    body[:3,:3]=body_rotation(row['body'])[0];body[:3,3]=row['body']['position']
    actual=np.array(center_of_mass(nav_robot_model,q,body))
    points=dict(zip(nav_robot_model.feet,row['contacts']['points']))
    loads=dict(zip(nav_robot_model.feet,row['contacts']['touching']))
    support=[point for name,point in points.items() if name!=row['swing_foot']]
    assert support_margin(actual,support)==pytest.approx(.009877044883909392,abs=1e-10)
    baseline=dict(q);baseline.update(value._solve(q,True))
    virtual=np.array(center_of_mass(nav_robot_model,baseline,value.reference_body))
    assert support_margin(virtual,support)>.025, 'original absolute model optimism no longer reproduced'
    start=value.reference_body.copy()
    value._begin_shift(actual,loads,points,row['ros_ns'],q)
    list(value._shift_plan)
    goal=start.copy();goal[:2,3]+=value._offset_goal-value._offset_start
    planned=dict(q);planned.update(value._solve(q,True,goal))
    delta=np.array(center_of_mass(nav_robot_model,planned,goal))-virtual
    assert support_margin(actual+delta,support)>=.025-1e-12, \
        'absolute virtual CoM accepted zero shift while the actual three-foot margin was below 10mm'
    assert np.linalg.norm(value._offset_goal-value._offset_start)>.001
