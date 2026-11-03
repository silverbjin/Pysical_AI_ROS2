import pytest
from ch13_manipulation_reuse.pick_feedback import lift_correction


def test_measured_endpoint_lag_is_compensated_within_single_three_cm_bound():
    assert lift_correction(.54,.625,.643,.629)==pytest.approx(.03)
    assert lift_correction(.54,.625,.63,.63)==pytest.approx(.018)
    assert lift_correction(.54,.637,.64,.63)==0.


@pytest.mark.parametrize('values',[(.54,float('nan'),.64,.63),(.54,.60,.64,.63)])
def test_nonfinite_or_large_lift_shortfall_is_rejected(values):
    with pytest.raises(ValueError):lift_correction(*values)
