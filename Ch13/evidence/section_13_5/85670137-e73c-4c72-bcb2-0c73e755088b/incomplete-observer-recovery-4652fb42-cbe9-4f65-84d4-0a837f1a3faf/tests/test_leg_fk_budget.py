"""Break: the verified3-axis hot path repeatedly solves general4x4 systems."""
import numpy as np
import pytest

from integrated_robot_navigation.leg_kinematics import fk_leg
from integrated_robot_navigation.model import compile_model


def test_verified_leg_fk_avoids_general_matrix_solve_without_changing_positions(nav_robot_model, monkeypatch):
    original = np.linalg.solve
    solves = []

    def counted(*args, **kwargs):
        solves.append(None)
        return original(*args, **kwargs)

    monkeypatch.setattr(np.linalg, 'solve', counted)
    expected = {'fr_foot': (.25, -.18, -.438791280945),
                'fl_foot': (.25, .18, -.438791280945),
                'rr_foot': (-.25, -.18, -.438791280945),
                'rl_foot': (-.25, .18, -.438791280945)}
    for foot, point in expected.items():
        assert fk_leg(nav_robot_model, foot, (0., -.5, 1.)) == pytest.approx(point, abs=1e-10)
    assert not solves, 'verified scalar leg geometry must not pay a dense root-frame solve every evaluation'


def test_general_fk_is_retained_for_a_different_hip_axis(nav_robot_model):
    import xml.etree.ElementTree as ET
    tree = ET.fromstring(nav_robot_model.urdf)
    tree.find("joint[@name='fr_hip_joint']/axis").set('xyz', '0 0 1')
    model = compile_model(ET.tostring(tree, encoding='unicode'))
    # Rz(.2)*(0,-.05,-.5) + hip(.25,-.13,0), independently calculated.
    assert fk_leg(model, 'fr_foot', (.2, 0., 0.)) == pytest.approx(
        (.2599334665397531, -.1790033288920621, -.5), abs=1e-12)


def test_analytic_fast_path_still_rejects_out_of_bound_feedback(nav_robot_model):
    with pytest.raises(ValueError):
        fk_leg(nav_robot_model, 'fr_foot', (.9, -.5, 1.))
