"""13.6.3 read-only capture-time camera -> map -> actual trunk equivalence."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation


def inspect(folder):
    run=Path(folder)/'run'
    sample=json.loads((run/'last_accepted_observation.json').read_text())
    sensors=json.loads((run/'sensor_summary.json').read_text())
    assert sample['source_frame']=='reuse/camera_optical' and sample['frame']=='reuse/map'
    assert 0<=sample['capture_ns']-sample['tf_stamp_ns']<=100_000_000
    Tbc=np.eye(4);Tbc[:3,3]=sensors['camera_pos_base_m']
    Tbc[:3,:3]=Rotation.from_quat(sensors['camera_optical_quat_base_xyzw']).as_matrix()
    Tmc=np.array(sample['T_map_camera']);Tmb=Tmc@np.linalg.inv(Tbc)
    source=np.r_[sample['optical_point'],1.];world=Tmc@source
    trunk_direct=Tbc@source;trunk_world=np.linalg.inv(Tmb)@world
    np.testing.assert_allclose(world[:3],sample['point'],atol=1e-9)
    np.testing.assert_allclose(trunk_direct,trunk_world,atol=1e-9)
    return dict(result='PASS',scope='offline coordinate inspection only; expired evidence is NOT motion authority',
                source_capture_ns=sample['capture_ns'],original_capture_wall=sample['capture_wall'],past_tf_stamp_ns=sample['tf_stamp_ns'],
                source_frame='reuse/camera_optical',point_camera_m=source[:3].tolist(),point_map_m=world[:3].tolist(),
                arm_reference_frame='reuse/base (actual trunk at historical TF stamp)',point_trunk_m=trunk_direct[:3].tolist(),
                T_map_trunk_at_tf_stamp=Tmb.tolist(),direct_vs_map_error_m=float(np.linalg.norm(trunk_direct[:3]-trunk_world[:3])))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('evidence');parser.add_argument('--output',type=Path);args=parser.parse_args()
    result=inspect(args.evidence)
    if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
