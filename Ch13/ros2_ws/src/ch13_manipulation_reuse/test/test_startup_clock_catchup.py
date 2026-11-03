"""Natural diagnostic 6cde23d3: clock arrived23.1ms later, processed174.7ms later."""
import pytest
from types import SimpleNamespace
from ch13_navigation_reuse.nav_contract import FutureInbox
from ch13_navigation_reuse.command_gateway import CommandGateway
from ch13_navigation_reuse.navigation_boundary import NavigationBoundary


def pending():
    box=FutureInbox();payload=object()
    box.offer('scan',162_000_000,56.724943588,payload,68_000_000,56.899195388)
    return box,payload


def test_real_native_clock_caught_up_in_time_despite_late_startup_processing():
    box,payload=pending()
    assert box.ready(180_000_000,56.899595188,clock_receipt=56.748077088,startup=True)==[payload]
    assert not box.items


def test_startup_timer_waits_for_native_clock_evidence_without_renewing_source_age():
    box,payload=pending()
    # Timer runs before the clock callback, although that clock was natively
    # received23.1ms after the source and is waiting in the Python queue.
    assert box.ready(68_000_000,56.899595188,clock_receipt=56.555098588,startup=True)==[]
    assert box.ready(180_000_000,56.900,clock_receipt=56.748077088,startup=True)==[payload]
    box,_=pending()
    with pytest.raises(ValueError,match='300wallms'):
        box.ready(68_000_000,57.026,clock_receipt=56.555098588,startup=True)


@pytest.mark.parametrize('clock_receipt,now',[(56.790,56.900),(56.748077088,57.026),(float('nan'),56.900),(56.91,56.90)])
def test_late_clock_old_source_and_invalid_receipt_still_fail(clock_receipt,now):
    box,_=pending()
    with pytest.raises(ValueError):box.ready(180_000_000,now,clock_receipt=clock_receipt,startup=True)


def test_active_mode_keeps_original_fifty_ms_deadline():
    box,_=pending()
    with pytest.raises(ValueError):box.ready(68_000_000,56.899595188,clock_receipt=56.555098588,startup=False)
    box,_=pending()
    with pytest.raises(ValueError):box.ready(180_000_000,56.899595188,clock_receipt=56.748077088,startup=False)


def test_pending_samples_cannot_arm_gateway_or_enable_navigation():
    gateway=CommandGateway.__new__(CommandGateway);called=[]
    gateway.guard=SimpleNamespace(samples={'raw':(1,)},arm=lambda wall:called.append(True) or True,
        mode='DISARMED',fault='',counts={});gateway.safe_watermark_ns=0;gateway.startup_sync=True
    gateway.pending=FutureInbox();gateway.pending.items['base']=(2,0.,None)
    response=gateway.on_arm(None,SimpleNamespace())
    assert not response.success and not called and gateway.startup_sync
    navigation=NavigationBoundary.__new__(NavigationBoundary);navigation.startup_sync=True
    navigation.c=SimpleNamespace(enable=lambda wall:called.append(True) or True,phase='IDLE')
    navigation.pending=gateway.pending
    response=navigation.enable(None,SimpleNamespace())
    assert not response.success and not called and navigation.startup_sync
    gateway.pending.items.clear()
    assert gateway.on_arm(None,SimpleNamespace()).success and not gateway.startup_sync
    assert navigation.enable(None,SimpleNamespace()).success and not navigation.startup_sync
