"""Actual lifecycle activation/DDS command, loaded fixture is not physics."""
from dataclasses import replace

import pytest
from lifecycle_msgs.msg import Transition

from guard_fixture import bundle as measured_bundle
from test_crawl_lifecycle import crawl_rig


def test_first_owned_command_preserves_native_initial_preload(crawl_rig, monkeypatch):
    rig = crawl_rig
    import test_motion_guard_ros

    def loaded(model):
        state = measured_bundle(model)
        q = dict(state.joints.data['position'])
        for prefix in ('fr', 'fl', 'rr', 'rl'):
            q[prefix+'_calf_joint'] = 1.035
        return replace(state, joints=replace(state.joints,
            data=dict(position=q, velocity=state.joints.data['velocity'])))

    monkeypatch.setattr(test_motion_guard_ros, 'bundle', loaded)
    rig.pump(.15)
    assert rig.transition(Transition.TRANSITION_CONFIGURE)
    assert rig.transition(Transition.TRANSITION_ACTIVATE)
    rig.pump(.08)
    assert rig.commands, 'activated sole owner emitted no position command'
    first = dict(zip(rig.model.joint_names, rig.commands[0].data))
    assert first['fr_calf_joint'] == pytest.approx(1., abs=1e-3)
    assert 500*(first['fr_calf_joint']-1.035) == pytest.approx(-17.5, abs=.5)
