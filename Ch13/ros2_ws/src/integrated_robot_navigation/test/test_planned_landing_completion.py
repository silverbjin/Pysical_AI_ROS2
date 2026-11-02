"""Early load must not latch an unfinished normal CRAWL command reference.

The 99ee5235 native failure left FL target z=0.02610256694, measured
floor=0.01871437781, then exhausted FR's unchanged 10mm unload budget.
This is a command-contract regression, NOT new native dynamics evidence.
"""
import numpy as np
import json
from pathlib import Path

from integrated_robot_navigation.support import center_of_mass, support_margin
from integrated_robot_navigation.projection import body_rotation
from integrated_robot_navigation.leg_kinematics import fk_leg

from test_landing_continuity import contact, descending_swing


def test_early_contact_does_not_latch_incomplete_planned_endpoint(nav_robot_model):
    plant, value, _ = descending_swing(nav_robot_model)
    foot = 'fl_foot'
    goal = value._swing_goal.copy()
    prior = value._targets[foot].copy()
    for _ in range(600):
        plant.tick(follow=False)
        contact(plant, True)
        result = value.advance(plant.state, (.0001, 0., 0.), plant.ros, plant.wall)
        assert result.state != 'FAULT', result.reason
        current = value._targets[foot].copy()
        assert np.linalg.norm(current-prior)/.02 <= .020000001
        prior = current
        if result.phase == 'SETTLE':
            assert np.allclose(current, goal, atol=1e-10), \
                'contact is not completion: raised/short reference would be inherited by next support shift'
            centers=value._measure(plant.state,plant.ros,plant.wall)[2]
            assert np.allclose(value.anchors[foot], centers[foot], atol=1e-10), \
                'slip baseline is measured independently of the completed command'
            return
    raise AssertionError('bounded original planned landing did not finish')


def test_recorded_failure_separates_reference_height_from_actual_lift(nav_robot_model):
    """Real saved q/body/contact; offline derived geometry, no simulated motion."""
    row = json.loads((Path(__file__).parent/'fixtures/g2_99ee5235_unload.json').read_text())
    body, contact = row['body']['data'], row['contacts']['data']
    pose=np.eye(4); pose[:3,:3]=body_rotation(body)[0];pose[:3,3]=body['position']
    q=row['joints']['data']['position']
    stance=[p for n,p in zip(contact['names'],contact['points']) if n!='fr_foot']
    assert support_margin(center_of_mass(nav_robot_model,q,pose),stance) > .01
    local=np.r_[fk_leg(nav_robot_model,'fr_foot',tuple(q['fr_'+part+'_joint']
                for part in ('hip','thigh','calf'))),1.]
    assert (pose@local)[2]-row['floor']['fr_foot'] < .001
    assert contact['forces'][0] > 20.  # reference +10mm did NOT unload this foot
    assert row['targets']['fl_foot'][2]-row['floor']['fl_foot'] > .007
