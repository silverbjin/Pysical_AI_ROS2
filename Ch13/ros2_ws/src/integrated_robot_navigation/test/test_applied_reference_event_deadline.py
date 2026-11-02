"""Application/first-receipt deadline is separate from owner evaluation time.

CF1 native application is proven; its ACK receipt was not recorded. These are
explicit synthetic receipt scenarios, not reconstructed CF1 wire evidence.
"""
import pytest
from integrated_robot_navigation.samples import Sample
from test_applied_reference_credit import gate,observed

ROS=1_000_000_000
WALL=10_000_000_000


def pending():
    value=gate();value.prime((0.,0.));value.submitted((.001,.002),ROS,WALL)
    return value


def test_timely_application_and_first_receipt_survive_delayed_owner_evaluation():
    value=pending()
    value.receive(observed((.001,.002),stamp=ROS+46_000_000,receipt=WALL+100_000_000))
    assert not value.permit(ROS+45_000_000,WALL+99_000_000),'future input was used'
    # CF1's measured decision offsets; receipt100ms is an explicit test input.
    # At this decision capture age164ms/receipt age106ms are BOTH still valid.
    assert value.permit(ROS+210_000_000,WALL+206_000_000)
    ack=value.snapshot()['last_ack']
    assert ack['stamp_ns']==ROS+46_000_000 and ack['received_ns']==WALL+100_000_000
    assert value.snapshot()['pending'] is None


@pytest.mark.parametrize('capture,receipt',[
    (200_000_001,100_000_000),(46_000_000,200_000_001),
])
def test_genuinely_late_capture_or_first_receipt_remains_unconfirmed(capture,receipt):
    value=pending()
    value.receive(observed((.001,.002),stamp=ROS+capture,receipt=WALL+receipt))
    with pytest.raises(ValueError,match='unconfirmed'):
        value.permit(ROS+210_000_000,WALL+206_000_000)
    assert value.snapshot()['pending'] is not None


def test_timely_but_now_stale_capture_still_cannot_release_credit():
    value=pending()
    value.receive(observed((.001,.002),stamp=ROS+1_000_000,receipt=WALL+1_000_000))
    with pytest.raises(ValueError,match='unconfirmed'):
        value.permit(ROS+210_000_000,WALL+206_000_000)


def test_timely_wrong_values_cannot_release_credit_after_deadline():
    value=pending()
    value.receive(observed((.003,.002),stamp=ROS+46_000_000,receipt=WALL+100_000_000))
    with pytest.raises(ValueError,match='unconfirmed'):
        value.permit(ROS+210_000_000,WALL+206_000_000)


def test_report_preserves_original_received_candidates_even_if_not_yet_usable():
    value=pending()
    sample=observed((.001,.002),stamp=ROS+46_000_000,receipt=WALL+100_000_000)
    value.receive(sample)
    value.receive(Sample(sample.stamp_ns,WALL+300_000_000,sample.epoch,sample.sequence,
        sample.frame_id,sample.data))
    snapshot=value.snapshot()
    received=snapshot['received_samples']
    assert len(received)==1 and received[0]['received_ns']==WALL+100_000_000
    received[0]['received_ns']=0
    assert value.snapshot()['received_samples'][0]['received_ns']==WALL+100_000_000
