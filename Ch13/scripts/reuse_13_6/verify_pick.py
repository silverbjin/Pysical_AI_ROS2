"""Recompute physical pick acceptance and saved RGB-D fit after engine exit."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from ch13_manipulation_reuse.pick_acceptance import assess_pick
from ch13_manipulation_reuse.cylinder_vision import fit_cylinder


def verify(path):
    path=Path(path);run=path/'run';summary=json.loads((run/'navigation_summary.json').read_text())
    assert summary['result']=='PASS',summary.get('error')
    assert not summary['gateway_last'].get('fault') and not summary['navigation_last'].get('fault')
    engine=json.loads((run/'engine.json').read_text())
    assert engine['normal_shutdown_requested'] and engine['rx_joined'] and engine['camera_worker_joined'] and engine['upstream_threads_joined']
    assert not engine['final_fault'] and engine['max_force_cap_ratio']<=1.+1e-8
    assert summary['clean_launch_exits']==12 and summary['planner_stopped_before_engine'] and not summary['remaining_launch_pids']
    assert json.loads((path/'post_residual.json').read_text())['result']=='PASS'
    physics=assess_pick(engine['pick_physics']['rows']);assert physics['result']=='PASS',physics
    meta=json.loads((run/'last_accepted_observation.json').read_text())
    rgb=np.array(Image.open(run/'last_accepted_rgb.png'));depth=np.load(run/'last_accepted_depth.npy')
    fit=fit_cylinder(rgb,depth,meta['calibration'],meta['T_map_camera'],.02,.08)
    assert np.allclose(fit['center'],meta['point'],atol=1e-9)
    assert 0<=meta['capture_ns']-meta['tf_stamp_ns']<=100_000_000
    mission=json.loads((run/'pick_mission.json').read_text())
    assert [x['phase'] for x in mission['stages'] if 'phase' in x]==['PRE_GRASP','GRASP_APPROACH','CLOSE','LIFT','HOLD','POST_SETTLE']
    paths=[r for r in mission['planning'] if r['kind']=='cartesian']
    assert len(paths)==2 and all(r['fraction']==1. for r in paths)
    return dict(result='PASS',physics=physics,saved_RGBD_center_recomputed=True,clean_children=12)


if __name__=='__main__':print(json.dumps([verify(p) for p in sys.argv[1:]],indent=2))
