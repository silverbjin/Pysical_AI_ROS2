"""Planning remains sliced and fails closed before any motor publication."""
import numpy as np
import pytest
from integrated_robot_navigation.contact_transfer import balanced_support_weight


def collect(predict):
    count=[]
    def measured(*args,**kwargs):
        count.append((args,kwargs));return predict(*args,**kwargs)
    plan=balanced_support_weight(0.,np.array([1.,1.]),measured,
        [(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)],.025,.7)
    while True:
        before=len(count)
        try:next(plan)
        except StopIteration as result:
            assert len(count)-before<=1
            return result.value
        assert len(count)-before<=1,'multiple full model predictions occupied one control slice'


def center(weight,direction,**kwargs):
    return np.array([.1+weight*(1/3-.1),.1+weight*(1/3-.1),.4])


def test_balance_search_has_bounded_single_prediction_slices():
    selected,report=collect(center)
    assert selected==1.
    assert report['proposed_fractions']==pytest.approx([1/3]*3)


@pytest.mark.parametrize('failure',['path','future'])
def test_rejected_improvement_retains_previously_proved_initial_path(failure):
    def predict(weight,direction,**kwargs):
        if ((failure=='path' and kwargs.get('progress')==.5)
                or (failure=='future' and 'horizon_budget' in kwargs)):
            raise ValueError('independent IK path rejection')
        return center(weight,direction)
    selected,report=collect(predict)
    assert selected==0. and report['path_rejection']=='independent IK path rejection'


def test_no_valid_balance_candidate_cannot_silently_authorize_translation():
    def invalid(*args,**kwargs):raise ValueError('no valid model candidate')
    with pytest.raises(ValueError,match='no valid support load candidate'):
        collect(invalid)
