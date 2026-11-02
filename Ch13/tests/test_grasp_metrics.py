from dataclasses import replace
import pytest
from ch13_sim_core.grasp_metrics import GraspObservation, classify_grasp

def observations():
    return [GraspObservation(t/10, True, True, .04, .01) for t in range(10)]

def test_requires_continuous_bilateral_lift_and_low_drift():
    r=classify_grasp(observations())
    assert r.success and r.hold_duration >= .5

@pytest.mark.parametrize('field,value', [('left_contact',False),('right_contact',False),('lift',.02),('drift',.03),('lift',float('nan'))])
def test_missing_each_physical_condition_fails(field,value):
    assert not classify_grasp([replace(o,**{field:value}) for o in observations()]).success

def test_short_or_interrupted_hold_fails():
    assert not classify_grasp(observations()[:4]).success
    seq=observations()
    seq[4]=replace(seq[4],right_contact=False)
    assert not classify_grasp(seq).success
