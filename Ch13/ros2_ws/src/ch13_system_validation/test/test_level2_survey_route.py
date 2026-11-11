"""Earlier observation waypoint preserves world, footprint and final scoring."""
import json
import math
from pathlib import Path
import pytest
from ch13_system_validation.scenarios import get_scenario


def test_level2_observes_before_the_saved_late_rotation_without_relaxing_goal(monkeypatch):
    monkeypatch.setenv('CH13_EXPERIMENTAL_SE2','0')
    scenario=get_scenario('level2_obstacles')
    assert scenario.survey_pose==pytest.approx((1.65,-.3,math.atan2(1.3,1.35)))
    assert scenario.target_xyz==(3.,1.,.54)
    assert scenario.approach_standoff_m==.8
    assert scenario.vision_hz==15
    assert scenario.record()['navigation_profile']=='baseline_forward_dubin'
    assert get_scenario('level3_house').vision_hz==15
    assert get_scenario('level3_house').survey_pose==pytest.approx((1.9,.4,math.atan2(.6,1.1)))


def test_earlier_survey_pose_passes_existing_filled_footprint(monkeypatch):
    from ch13_navigation_reuse.scene import map_layout
    from ch13_navigation_reuse.approach_geometry import footprint_clear
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1')
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO','level2_obstacles')
    root=Path(__file__).resolve().parents[5]
    footprint=json.loads((root/'Ch13/ros2_ws/src/ch13_navigation_reuse/config/footprint.json').read_text())['footprint']
    grid=dict(width=120,height=100,resolution=.05,origin=[-2.,-2.5],data=[])
    obstacles=map_layout('vision')
    for y in range(100):
        for x in range(120):
            px=-2+(x+.5)*.05;py=-2.5+(y+.5)*.05
            grid['data'].append(100 if any(abs(px-p[0])<=s[0]+.025 and abs(py-p[1])<=s[1]+.025 for _,p,s in obstacles) else 0)
    assert footprint_clear(get_scenario('level2_obstacles').survey_pose,grid,footprint)
