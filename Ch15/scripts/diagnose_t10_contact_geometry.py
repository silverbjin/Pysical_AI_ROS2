#!/usr/bin/env python3
"""Static native collision geometry at preserved states; never execute a mission."""
import argparse, hashlib, json, os, sys
from pathlib import Path
import mujoco
import numpy as np

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native',type=Path,required=True)
    p.add_argument('--fixture',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    root=args.native.resolve()
    os.environ.update(CH13_VALIDATION_PROFILE='carry_v1',CH13_VALIDATION_SCENARIO='level2_obstacles')
    for name in ('ch13_navigation_reuse','ch13_manipulation_reuse','ch13_system_validation'):
        sys.path.insert(0,str(root/'Ch13/ros2_ws/src'/name))
    from ch13_manipulation_reuse.pick_scene import make_pick_model
    assert mujoco.__version__=='3.13.0'
    up=root.parent/'upstream-iit-locomanipulation-d010212'
    lock=json.loads((root/'Ch13/dependencies/section_13_5_reuse.lock.json').read_text())
    assert len(lock['files'])==94
    assert all(hashlib.sha256((up/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in lock['files'])
    model=make_pick_model(up/'robot_model/scene_rough.xml')
    assert (model.nq,model.nv,model.nu)==(34,32,19)
    calf=model.body('RR_calf').id
    calf_geoms=[g for g in range(model.ngeom) if model.geom_bodyid[g]==calf and (model.geom_contype[g] or model.geom_conaffinity[g])]
    world_geoms=[g for g in range(model.ngeom) if model.geom_bodyid[g]==0 and model.geom_group[g]==5]
    assert calf_geoms and world_geoms
    result=[]
    for row in json.loads(args.fixture.read_text())['cases']:
        data=mujoco.MjData(model)
        q=np.asarray(row['qpos'],dtype=float)
        assert q.shape==(34,) and np.isfinite(q).all()
        data.qpos[:]=q
        mujoco.mj_forward(model,data)
        contacts=[]
        for c in data.contact:
            a,b=map(int,c.geom)
            if (a in calf_geoms and b in world_geoms) or (b in calf_geoms and a in world_geoms):
                contacts.append(dict(geom1=model.geom(a).name,geom2=model.geom(b).name,distance_m=float(c.dist)))
        distances=[]
        for a in calf_geoms:
            for b in world_geoms:
                segment=np.zeros(6,dtype=float)
                d=float(mujoco.mj_geomDistance(model,data,a,b,1.,segment))
                distances.append(dict(calf=model.geom(a).name,world=model.geom(b).name,distance_m=d))
        distances.sort(key=lambda r:r['distance_m'])
        result.append(dict(run=row['run'],sim_s=row['sim_s'],contacts=contacts,nearest=distances[:8]))
    output=dict(scope='static geometry only; post-step states, not exact failing integration contact; no dynamics, no L2 verdict',cases=result)
    args.out.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    print(json.dumps(output,indent=2,allow_nan=False))
if __name__=='__main__':
    main()
