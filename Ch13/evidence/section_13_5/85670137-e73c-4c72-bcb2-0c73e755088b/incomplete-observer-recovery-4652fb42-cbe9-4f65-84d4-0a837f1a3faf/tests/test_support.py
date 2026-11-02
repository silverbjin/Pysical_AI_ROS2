"""Breaks caught: wrong polygon winding, lifting on edge, degenerate support."""
import importlib
import pytest


def margin(point, contacts):
    assert importlib.util.find_spec('integrated_robot_navigation.support'), 'support core missing'
    return importlib.import_module('integrated_robot_navigation.support').support_margin(point, contacts)


def test_support_margin_literal_square_and_triangle():
    square = [(-.2, -.1, 0.), (.2, -.1, 0.), (.2, .1, 0.), (-.2, .1, 0.)]
    assert margin((0., 0., 0.), square) == pytest.approx(.1)
    assert margin((0., 0., 0.), square[::-1]) == pytest.approx(.1)
    assert margin((.3, 0., 0.), square) == pytest.approx(-.1)
    assert margin((0., 0., 0.), square[:3]) == pytest.approx(0.)
    assert margin((0., 0., 0.), square[:3]) < .01


@pytest.mark.parametrize('contacts', [
    [(0., 0., 0.), (1., 0., 0.)],
    [(0., 0., 0.), (1., 0., 0.), (2., 0., 0.)],
    [(0., 0., 0.), (1., 0., 0.), (float('nan'), 1., 0.)],
    [(0., 0., 0.), (1., 0., 0.), (0., 0., 0.)],
])
def test_invalid_support_is_rejected(contacts):
    with pytest.raises(ValueError):
        margin((0., 0., 0.), contacts)
