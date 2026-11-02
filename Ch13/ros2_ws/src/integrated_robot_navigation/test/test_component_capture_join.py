"""Causal capture association; mismatched latest values are not a sensor loss."""
import json
from pathlib import Path
import pytest
from integrated_robot_navigation import contact_component as module
from integrated_robot_navigation.samples import Sample,sample_valid
from test_contact_component import frame,tracker


def api():
    assert hasattr(module,'ComponentCaptureJoiner'), 'component still combines independently latest body/joints/contact captures'
    return module.ComponentCaptureJoiner


def test_actual_mission_mismatch_is_reproduced_then_joined_without_relaxing_40ms(nav_robot_model):
    data=json.loads((Path(__file__).parent/'fixtures/bcec_component_capture_join.json').read_text())
    bad=data['first_mismatch']['samples'];ros=max(s['stamp_ns'] for s in bad.values());wall=max(s['received_ns'] for s in bad.values())
    value=tracker(nav_robot_model)
    with pytest.raises(ValueError,match='capture mismatch'):
        value._read(dict(samples=bad,ros_ns=ros,wall_ns=wall))
    join=api()();first={};accepted=[];started=False
    for row in data['rows']:
        key=row['key'];sample=Sample(**row['sample']);first.setdefault((key,sample.stamp_ns),sample.received_ns)
        join.receive(key,sample);ros=max(ros,sample.stamp_ns);wall=max(wall,sample.received_ns)
        if not started:
            item=join.begin(ros,wall)
            if item is None:continue
            started=True
        else:item=join.take(ros,wall)
        if item is None:continue
        accepted.append(item)
    assert started and len(accepted)>1
    stamps=[v['samples']['contacts']['stamp_ns'] for v in accepted]
    assert stamps==sorted(set(stamps))
    for item in accepted:
        samples={k:Sample(**s) for k,s in item['samples'].items()}
        assert max(s.stamp_ns for s in samples.values())-min(s.stamp_ns for s in samples.values())<=40_000_000
        for k,s in samples.items():
            assert sample_valid(s,item['ros_ns'],item['wall_ns'],0,max_age_ns=200_000_000)[0]
            assert s.received_ns==first[k,s.stamp_ns]
    join.close();assert join.report()['closed']


def test_unmatched_contact_expires_as_failure_instead_of_skipping_to_newer(nav_robot_model):
    join=api()();base=frame(nav_robot_model)
    for k in ('joints','body','contacts'):join.receive(k,Sample(**base['samples'][k]))
    assert join.begin(base['ros_ns'],base['wall_ns']) is not None
    late=frame(nav_robot_model,1_080_000_000,10_080_000_000)
    join.receive('contacts',Sample(**late['samples']['contacts']))
    assert join.take(late['ros_ns'],late['wall_ns']) is None
    # Even with all streams newly fresh, the earlier unmatched contact must
    # expire as a failure instead of being skipped for the new coherent one.
    newer=frame(nav_robot_model,1_280_000_001,10_280_000_001)
    for k in ('joints','body','contacts'):join.receive(k,Sample(**newer['samples'][k]))
    with pytest.raises(ValueError,match='pending contact expired'):
        join.take(1_280_000_001,10_280_000_001)


def test_duplicate_does_not_renew_receipt_or_skip_a_high_force_capture(nav_robot_model):
    join=api()();base=frame(nav_robot_model);foot=nav_robot_model.feet[0]
    for k in ('joints','body','contacts'):join.receive(k,Sample(**base['samples'][k]))
    assert join.begin(base['ros_ns'],base['wall_ns'])
    for offset,force in ((20,0.),(40,30.),(60,0.)):
        f=frame(nav_robot_model,1_000_000_000+offset*1_000_000,10_000_000_000+offset*1_000_000,foot,.006,force)
        join.receive('contacts',Sample(**f['samples']['contacts']))
    last=frame(nav_robot_model,1_060_000_000,10_060_000_000,foot,.006,0.)
    for k in ('joints','body'):join.receive(k,Sample(**last['samples'][k]))
    emitted=[]
    while (v:=join.take(1_060_000_000,10_060_000_000)) is not None:emitted.append(v)
    assert [v['samples']['contacts']['data']['forces'][0] for v in emitted]==[0.,30.,0.]
    assert [v['samples']['contacts']['stamp_ns'] for v in emitted]==[1_020_000_000,1_040_000_000,1_060_000_000]
    repeated=Sample(**last['samples']['contacts']);join.receive('contacts',repeated)
    assert join.take(1_080_000_000,10_080_000_000) is None


def test_closed_joiner_has_no_new_evidence(nav_robot_model):
    join=api()();join.close()
    join.receive('contacts',Sample(**frame(nav_robot_model)['samples']['contacts']))
    assert join.take(1_000_000_000,10_000_000_000) is None
