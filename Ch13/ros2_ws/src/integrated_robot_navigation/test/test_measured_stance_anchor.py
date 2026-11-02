"""Use recorded native offset to distinguish stance motion from servo error.

The TD/SETTLE transition below is an offline counterfactual replay of the
recorded state, not a new native run or a claim about its actual phase timing.
"""
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.samples import Sample
from guard_fixture import bundle


def replay(model):
    row=json.loads((Path(__file__).parent/'fixtures/g2_69f58225_stance.json').read_text())
    state=replace(bundle(model),**{key:Sample(**value) for key,value in row['samples'].items()})
    value=CrawlMachine(model,default_limits());value.reset(state,row['ros_ns'],row['wall_ns'])
    value.state,value.phase,value.swing_foot='CRAWL','TOUCHDOWN','rl_foot'
    value._index=3
    value.reference_body=np.array(row['reference_body']);value.travel=value.reference_body.copy()
    value.offset=np.zeros(2);value._targets={n:np.array(p) for n,p in row['targets'].items()}
    value.floor=row['floor']
    duration=value._body_duration('TOUCHDOWN',.25)
    value._phase_start=row['ros_ns']-int((duration+.02)*1e9)
    value._travel_token=('TOUCHDOWN',value._phase_start);value._travel_progress=.25
    return row,state,value


def test_completed_landing_does_not_invent_slip_from_command_tracking_error(nav_robot_model):
    row,state,value=replay(nav_robot_model)
    before={n:p.copy() for n,p in value._targets.items()}
    landed=value.advance(state,(.01,0.,0.),row['ros_ns'],row['wall_ns'])
    assert landed.state!='FAULT' and landed.phase=='SETTLE',landed.reason
    assert all(np.allclose(value._targets[n],p,atol=1e-12) for n,p in before.items()), \
        'measured baseline is not a new motor position target'
    after=value.advance(state,(.01,0.,0.),row['ros_ns']+20_000_000,row['wall_ns']+20_000_000)
    assert after.state!='FAULT', 'stationary measured foot was compared against a command anchor: '+after.reason


def test_actual_motion_beyond_unchanged_stance_limit_still_faults(nav_robot_model):
    row,state,value=replay(nav_robot_model)
    value.advance(state,(.01,0.,0.),row['ros_ns'],row['wall_ns'])
    # A real measured root/feet translation after landing must still fail.
    data={**state.body.data,'position':tuple(np.array(state.body.data['position'])+(.021,0.,0.))}
    moved=replace(state,body=replace(state.body,data=data))
    result=value.advance(moved,(.01,0.,0.),row['ros_ns']+20_000_000,row['wall_ns']+20_000_000)
    assert result.state=='FAULT' and result.reason=='stance slip'


def test_stop_contact_does_not_rewind_motor_reference_to_measured_world_center(nav_robot_model):
    row,state,value=replay(nav_robot_model)
    value.phase,value.swing_foot,value._index='SWING','fl_foot',0
    before=value._solve(state.joints.data['position'],True)
    value.request_stop(urgent=False)
    result=value.advance(state,(.01,0.,0.),row['ros_ns'],row['wall_ns'])
    assert result.state!='FAULT',result.reason
    assert max(abs(result.joint_targets[n]-q) for n,q in before.items())<1e-10, \
        'stop at first contact mixed the measured stance frame with motor command references'
