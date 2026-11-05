from collections import Counter
from ch13_navigation_reuse.vision_approach import VisionObserver


def observer(allow,seen=False):
    node=VisionObserver.__new__(VisionObserver)
    node.allow_initial_absence=allow;node.rows=[{}] if seen else []
    node.rejected=Counter();node.fault=''
    return node


def test_initial_survey_absence_is_counted_without_latching_sensor_fault():
    node=observer(True)
    node.record_rejection('cylinder not observed')
    assert node.fault=='' and node.rejected['cylinder not observed']==1
    node.rows.append({'source':'actual accepted observation'})
    node.record_rejection('cylinder not observed')
    assert node.fault=='TARGET_NOT_OBSERVED'


def test_legacy_absence_and_non_cylinder_absence_still_latch():
    for allow,reason in ((False,'cylinder not observed'),(True,'red fixture not observed')):
        node=observer(allow);node.record_rejection(reason)
        assert node.fault=='TARGET_NOT_OBSERVED'
