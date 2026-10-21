"""A time delay is not evidence of pre-control pixel measurements."""
import run_vision_13_4 as runner


def test_baseline_requires_three_unique_precontrol_measurements():
    samples = [dict(capture_ns=11, wall=10.1, pixel_error=6.),
               dict(capture_ns=12, wall=10.2, pixel_error=5.),
               dict(capture_ns=12, wall=10.3, pixel_error=5.)]
    assert runner.tracking_baseline(samples, 10.) is None
    samples.append(dict(capture_ns=13, wall=10.4, pixel_error=7.))
    baseline = runner.tracking_baseline(samples, 10.)
    assert baseline['capture_ns'] == [11, 12, 13]
    assert baseline['pixel_errors'] == [6., 5., 7.]
    assert baseline['measurement_walls'] == [10.1, 10.2, 10.4]


def test_elapsed_warmup_cannot_replace_missing_or_invalid_baseline():
    assert runner.tracking_baseline([], 10.) is None
    samples = [dict(capture_ns=i, wall=9., pixel_error=6.) for i in (1, 2, 3)]
    assert runner.tracking_baseline(samples, 10.) is None
    for sample in samples:
        sample['wall'] = 11.
        sample['pixel_error'] = .5
    assert runner.tracking_baseline(samples, 10.) is None  # original >1px requirement
