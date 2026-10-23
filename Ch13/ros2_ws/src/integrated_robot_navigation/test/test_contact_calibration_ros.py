"""The native G1 probe cannot acquire a second leg publisher or bypass CRAWL."""
import time
import pytest
from lifecycle_msgs.msg import Transition
from std_srvs.srv import Trigger
from test_crawl_lifecycle import crawl_rig


@pytest.mark.parametrize('crawl_rig', [True, False], indirect=True)
def test_inplace_calibration_requires_validation_mode_and_measured_carry(crawl_rig):
    rig = crawl_rig
    assert rig.transition(Transition.TRANSITION_CONFIGURE)
    assert rig.transition(Transition.TRANSITION_ACTIVATE)
    rig.pump(1.15)
    assert rig.crawl_states[-1].stopped
    client = rig.node.create_client(Trigger, '/crawl_controller/calibrate_contact')
    assert client.wait_for_service(timeout_sec=1.)

    def call():
        future = client.call_async(Trigger.Request())
        end = time.monotonic()+1.
        while not future.done() and time.monotonic() < end:
            rig.pump(.02)
        assert future.done()
        return future.result()

    assert not call().success  # bootstrap was intentionally before ready carry
    rig.ready = True
    rig.pump(.06)
    response = call()
    assert response.success is rig.guard.validation_mode
    rig.pump(.08)
    assert rig.node.count_publishers('/leg_position_controller/commands') == 1
    assert rig.crawl_states[-1].state != 'CRAWL'
    if response.success:
        assert rig.crawl_states[-1].state == 'CALIBRATING'
