"""Applied values, rather than command receipt, return one trajectory credit."""
import importlib.util
import importlib
import pytest
from integrated_robot_navigation.samples import Sample


def gate():
    assert importlib.util.find_spec('integrated_robot_navigation.applied_reference'), \
        'native applied-reference credit contract missing'
    return importlib.import_module('integrated_robot_navigation.applied_reference').AppliedReferenceCredit(
        ('rr_calf_joint','rr_thigh_joint'))


def observed(values,stamp=110,receipt=1010,sequence=1):
    return Sample(stamp,receipt,0,sequence,'mujoco/pre_step',
        {'name':('rr_thigh_joint','arm_joint_1','rr_calf_joint'),
         'position':(values[1],0.,values[0])})


def test_single_outstanding_goal_prevents_reproduced_native_skipped_references():
    value=gate(); value.prime((1.0317002897511454,-.5211113950502206))
    value.submitted((1.0304379075569743,-.5207),100,1000)
    assert not value.permit(110,1010)
    with pytest.raises(ValueError,match='outstanding'):
        value.submitted((1.0272771906801002,-.5200),120,1020)
    # CM/staging receipt is explicitly the wrong boundary.
    wrong=observed((1.0304379075569743,-.5207))
    value.receive(Sample(wrong.stamp_ns,wrong.received_ns,0,1,'mujoco/cm_write',wrong.data))
    assert not value.permit(120,1020)
    value.receive(observed((1.0304379075569743,-.5207),stamp=125,receipt=1025,sequence=2))
    assert value.permit(130,1030)
    value.submitted((1.0272771906801002,-.5200),130,1030)
    assert not value.permit(140,1040)


def test_duplicate_or_future_receipts_cannot_retag_acknowledgement():
    value=gate();value.prime((0.,0.));value.submitted((.001,.002),100,1000)
    value.receive(observed((.001,.002),stamp=90,receipt=990))
    value.receive(observed((.001,.002),stamp=90,receipt=1010))
    assert not value.permit(110,1020)
    value.receive(observed((.001,.002),stamp=140,receipt=1040,sequence=2))
    assert not value.permit(130,1050)
    assert value.permit(140,1050)
    assert value.snapshot()['last_ack']['received_ns']==1040


def test_republishing_pending_target_does_not_extend_original_deadline():
    value=gate();value.prime((0.,0.));value.submitted((.001,.002),100,1000)
    value.submitted((.001,.002),100_000_100,100_001_000)
    with pytest.raises(ValueError,match='unconfirmed'):
        value.permit(200_000_101,200_001_001)
    assert value.snapshot()['pending']['issued_wall_ns']==1000


def test_stop_abandons_credit_without_claiming_application_or_auto_recovery():
    value=gate();value.prime((0.,0.));value.submitted((.001,.002),100,1000)
    value.suspend('measured_stop_path')
    report=value.snapshot()
    assert report['last_ack'] is None and report['pending'] is None
    assert report['events'][-1]['event']=='abandoned_for_stop'


def test_true_one_nanosecond_future_application_is_still_rejected():
    value=gate();value.prime((0.,0.));value.submitted((.001,.002),100,1000)
    value.receive(observed((.001,.002),stamp=141,receipt=1010))
    assert not value.permit(140,1020),'serialization fix cannot relax future-data rejection'
    assert value.snapshot()['pending'] is not None
    assert value.permit(141,1020)
