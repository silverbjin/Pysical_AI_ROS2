"""Recompute physical pick acceptance and saved RGB-D fit after engine exit."""
import json
import hashlib
import struct
import sys
import zlib
from pathlib import Path
import numpy as np
from ch13_manipulation_reuse.pick_acceptance import assess_pick,assess_held_cancel
from ch13_manipulation_reuse.cylinder_vision import fit_cylinder


def read_saved_rgb(path):
    # The repository's write_rgb emits RGB8 PNG, filter0, no interlace.
    # Read that exact format without adding a Pillow/install dependency.
    data=path.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n';cursor=8;blocks=[];shape=None
    while cursor<len(data):
        size=struct.unpack('>I',data[cursor:cursor+4])[0];kind=data[cursor+4:cursor+8]
        payload=data[cursor+8:cursor+8+size];crc=struct.unpack('>I',data[cursor+8+size:cursor+12+size])[0]
        assert zlib.crc32(kind+payload)&0xffffffff==crc
        if kind==b'IHDR':shape=struct.unpack('>IIBBBBB',payload)
        if kind==b'IDAT':blocks.append(payload)
        cursor+=size+12
        if kind==b'IEND':break
    assert shape==(320,240,8,2,0,0,0)
    decoder=zlib.decompressobj();raw=decoder.decompress(b''.join(blocks),240*961+1)
    assert decoder.eof and len(raw)==240*961
    rows=np.frombuffer(raw,dtype=np.uint8).reshape(240,961);assert np.all(rows[:,0]==0)
    return rows[:,1:].reshape(240,320,3).copy()


def verify(path,held_cancel=False):
    path=Path(path);run=path/'run';summary=json.loads((run/'navigation_summary.json').read_text())
    assert summary['result']=='PASS',summary.get('error')
    assert not summary['gateway_last'].get('fault') and not summary['navigation_last'].get('fault')
    engine=json.loads((run/'engine.json').read_text())
    assert engine['normal_shutdown_requested'] and engine['rx_joined'] and engine['camera_worker_joined'] and engine['upstream_threads_joined']
    assert not engine['final_fault'] and engine['max_force_cap_ratio']<=1.+1e-8
    assert summary['clean_launch_exits']==12 and summary['planner_stopped_before_engine'] and not summary['remaining_launch_pids']
    assert json.loads((path/'post_residual.json').read_text())['result']=='PASS'
    physics=(assess_held_cancel if held_cancel else assess_pick)(engine['pick_physics']['rows']);assert physics['result']=='PASS',physics
    meta=json.loads((run/'last_accepted_observation.json').read_text())
    rgb=read_saved_rgb(run/'last_accepted_rgb.png');depth=np.load(run/'last_accepted_depth.npy')
    assert hashlib.sha256(rgb.tobytes()).hexdigest()==meta['rgb_sha256']
    fit=fit_cylinder(rgb,depth,meta['calibration'],meta['T_map_camera'],.02,.08)
    assert np.allclose(fit['center'],meta['point'],atol=1e-9)
    assert 0<=meta['capture_ns']-meta['tf_stamp_ns']<=100_000_000
    mission=json.loads((run/'pick_mission.json').read_text())
    assert [x['phase'] for x in mission['stages'] if 'phase' in x]==['PRE_GRASP','GRASP_APPROACH','CLOSE','LIFT','HOLD','POST_SETTLE']
    paths=[r for r in mission['planning'] if r['kind']=='cartesian']
    assert 2<=len(paths)<=3 and all(r['fraction']==1. for r in paths)
    assert engine['manipulation']['gripper_force_events']
    corrections=[r for r in mission['stages'] if 'visual_correction_m' in r]
    assert len(corrections)<=1 and all(0<r['visual_correction_m']<=.03 for r in corrections)
    canceled=[e for e in engine['manipulation']['arm_events'] if e['event']=='measured_terminal' and e.get('terminal')=='canceled']
    if held_cancel:
        assert len(canceled)==1 and any(r.get('held_cancel') for r in mission['stages'])
        assert engine['manipulation']['last_status']['gripper_force_hold']['ready']
        assert not corrections
    else:assert not canceled
    return dict(result='PASS',physics=physics,saved_RGBD_center_recomputed=True,clean_children=12)


if __name__=='__main__':print(json.dumps([verify(p) for p in sys.argv[1:]],indent=2))
