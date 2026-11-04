from ch13_system_validation.transport import fresh_return_capture


def test_reentry_waits_for_original_capture_headroom_instead_of_renewing_it():
    boundary=dict(phase='IDLE',fault='',vision_capture_wall=4491.01159245)
    assert not fresh_return_capture(boundary,4491.313861819)
    boundary['vision_capture_wall']=4491.64286296
    assert fresh_return_capture(boundary,4491.707250514)


def test_capture_headroom_never_overrides_fault_or_missing_source_time():
    assert not fresh_return_capture(dict(phase='IDLE',fault='VISION_EXPIRED',vision_capture_wall=10.),10.05)
    assert not fresh_return_capture(dict(phase='IDLE',fault='',vision_capture_wall=None),10.05)
