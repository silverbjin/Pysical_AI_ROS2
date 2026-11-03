import copy
import pytest
from ch13_manipulation_reuse.pick_acceptance import assess_pick


def rows():
    result=[]
    for t,phase,z in [(0.,'PRE_GRASP',.54),(.5,'PRE_GRASP',.54),(1.,'CLOSE',.54),
                      (1.5,'LIFT',.60),(2.,'HOLD',.64),(3.,'HOLD',.64),(4.1,'HOLD',.64)]:
        result.append(dict(sim_s=t,phase=phase,target=[1.8,0.,z],relative_tcp=[0.,0.,.0],
                           target_contact_N={'link7':.1,'link8':.1}))
    return result


def test_real_lift_dual_contact_and_two_second_hold_required():
    assert assess_pick(rows())['result']=='PASS'


@pytest.mark.parametrize('failure',['no_lift','short_hold','slip','one_finger'])
def test_attach_or_controller_success_alone_is_insufficient(failure):
    data=rows()
    for row in data:
        if failure=='no_lift':row['target'][2]=.54
        if failure=='short_hold' and row['phase']=='HOLD':row['sim_s']=2.+(row['sim_s']-2.)*.2
        if failure=='one_finger':row['target_contact_N']['link8']=0.
    if failure=='slip':data[-1]['relative_tcp'][0]=.03
    assert assess_pick(data)['result']=='FAIL'
