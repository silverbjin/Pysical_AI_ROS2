"""No engines: preflight failures stay recorded and all moving stages audited."""
from dataclasses import asdict
import json
from types import SimpleNamespace
import pytest
import run_navigation_13_5 as runner
import verify_navigation_13_5 as verify
from guard_fixture import bundle
from integrated_robot_navigation.carry_profile import default_limits


def test_missing_g1_records_failed_g2_before_any_engine_or_command_source(tmp_path,monkeypatch):
    output=tmp_path/'fresh'
    def forbidden(*args,**kwargs):raise AssertionError('G2 started without G1')
    monkeypatch.setattr(runner.subprocess,'Popen',forbidden)
    args=SimpleNamespace(engine='mujoco',scenario='crawl-cycle',scene_dir=str(tmp_path/'missing'),
        profile=str(tmp_path/'missing.json'),output_dir=str(output),control_clock_mode='native',
        dart_contact_mode='native',profile_node=None,g1_result=None)
    with pytest.raises((RuntimeError,ValueError)):runner.run(args)
    assert (output/'result.json').is_file(),'G2 refusal did not preserve a result'
    result=json.loads((output/'result.json').read_text())
    assert result['gate']=='G2' and result['status']=='FAIL' and result['engine_started'] is False
    assert verify.G2_REQUIRED.issubset(result['required_checks'])


def test_known_moving_stages_are_retained_instead_of_filtered():
    rows=[dict(stage=name) for name in ('bootstrap','stand','forward','left','right','reverse','stopped','shutdown')]
    assert verify.operational_frames(rows)==rows[1:-1]


def test_reverse_assessment_does_not_waive_full_cycle_checks(nav_robot_model,monkeypatch):
    # Only exercise direction/phase arithmetic here; physical assessment is stubbed.
    monkeypatch.setattr(verify,'assess_frames',lambda *_:{key:True for key in verify.FRAME_REQUIRED})
    samples=asdict(bundle(nav_robot_model))
    observations=dict(root_source='native_ground_truth',phases=dict(
        stand=dict(ros_duration_s=10.,wall_duration_s=10.),reverse=dict(start=(0.,0.,0.),end=(-.1,0.,0.))),
        stopped_frames=[dict(ros_ns=t,wall_ns=t,samples=samples,crawl=dict(stopped=True)) for t in (1_000_000_000,2_000_000_000)])
    reverse=verify.assess_crawl(observations,default_limits(),scenario='crawl-reverse')
    assert all(reverse.values()) and 'reverse' in reverse and 'forward' not in reverse
    full=verify.assess_crawl(observations,default_limits())
    assert full['forward'] is False and full['left'] is False and full['right'] is False
