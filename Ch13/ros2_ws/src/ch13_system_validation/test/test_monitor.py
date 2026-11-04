import pytest
from ch13_system_validation.monitor import TopicStats,cpu_percent


def test_frequency_uses_receipt_interval_and_delay_keeps_capture_age():
    topic=TopicStats()
    topic.add(1_000_000_000,10.,clock_ns=1_050_000_000,capture_wall=9.92)
    topic.add(1_100_000_000,10.1,clock_ns=1_180_000_000,capture_wall=10.01)
    report=topic.report()
    assert report['receipt_hz']==pytest.approx(10.)
    assert report['mean_sim_delay_s']==pytest.approx(.065)
    assert report['max_capture_age_wall_s']==pytest.approx(.09)


def test_clock_rollback_and_missing_timestamp_remain_visible():
    topic=TopicStats();topic.add(10,1.,clock_ns=20);topic.add(5,2.,clock_ns=10)
    topic.add(None,3.,clock_ns=10)
    assert topic.report()['reordered']==1
    assert topic.report()['missing_stamps']==1


def test_process_cpu_normalized_by_allowed_cores():
    assert cpu_percent(2.,1.,4)==50.
    with pytest.raises(ValueError):cpu_percent(2.,0.,4)
