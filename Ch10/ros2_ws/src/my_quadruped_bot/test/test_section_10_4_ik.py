"""Inverse kinematics numeric regression: Ch10 URDF-derived nominal parameters."""
import numpy as np
import pytest
from my_quadruped_bot.inverse_kinematics import InverseKinematics


@pytest.mark.parametrize('right', (False, True))
def test_fk_ik_roundtrip_both_sides(right):
    ik = InverseKinematics()
    rng = np.random.default_rng(42)
    for _ in range(100):
        q = np.array([rng.uniform(-.3, .3),
                      rng.uniform(-.8, .3),
                      rng.uniform(-.7, 1.6)])
        point = ik.forward(q, right)
        solved = ik.solve(*point, is_right_leg=right)
        assert solved is not None
        assert np.linalg.norm(ik.forward(solved, right) - point) < 1e-6


@pytest.mark.parametrize('right', (False, True))
def test_nominal_stand(right):
    ik = InverseKinematics()
    p = np.array([0., -0.05 if right else 0.05, -0.3])
    q = ik.solve(*p, is_right_leg=right)
    assert q is not None
    np.testing.assert_allclose(ik.forward(q, right), p, atol=1e-6)


@pytest.mark.parametrize('p', ((2, 0, -.3), (0, 0, 0), (float('nan'), 0, -.3)))
def test_unreachable_or_nonfinite_rejected(p):
    assert InverseKinematics().solve(*p) is None


def test_link_constants_match_xacro():
    ik = InverseKinematics()
    assert ik.l2 == ik.l3 == 0.25
    assert ik.l1 == 0.05
    assert ik.thigh_origin_pitch == 1.2
    assert ik.calf_origin_pitch == -2.4
