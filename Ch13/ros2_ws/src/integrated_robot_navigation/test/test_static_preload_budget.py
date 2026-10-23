"""Measured native static force budget must fit unchanged stand tracking gate."""
import xml.etree.ElementTree as ET

from integrated_robot_navigation.geometry import navigation_mjcf


def test_calf_measured_static_load_fits_three_centiradian_readiness(nav_robot_model):
    # Run64989f80, last5ROSs of recorded bootstrap: max front calf position
    # force17.75Nm, below the unchanged30Nm cap. Round UP to18Nm for this
    # design-budget test. This arithmetic is NOT native G1/G2 acceptance.
    xml = ET.fromstring(navigation_mjcf(nav_robot_model))
    for prefix in ('fr', 'fl', 'rr', 'rl'):
        motor = xml.find(f"actuator/position[@joint='{prefix}_calf_joint']")
        assert 18./float(motor.get('kp')) <= .03
        assert list(map(float, motor.get('forcerange').split())) == [-30., 30.]
