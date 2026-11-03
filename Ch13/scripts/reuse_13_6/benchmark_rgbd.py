"""Render-only comparison, no actor/ROS control or physical success claim."""
import json
import sys
import time
from pathlib import Path
import numpy as np
import mujoco
root=Path(__file__).resolve().parents[3]
for package in ('ch13_navigation_reuse','ch13_manipulation_reuse'):sys.path.insert(0,str(root/'Ch13/ros2_ws/src'/package))
from ch13_navigation_reuse.camera_worker import render_rgbd
from ch13_manipulation_reuse.pick_scene import make_pick_model


def main():
    model=make_pick_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml')
    model.vis.quality.offsamples=0;data=mujoco.MjData(model)
    actual=root/'Ch13/evidence/section_13_6_reuse/5cadca4e-0f76-4f2e-9c86-50daeb694d64/run/engine_observations.jsonl'
    states=[model.key_qpos[model.key('home').id],np.array(json.loads(actual.read_text().splitlines()[-1])['qpos'])]
    option=mujoco.MjvOption();option.geomgroup[2]=0;option.geomgroup[3]=1;option.geomgroup[5]=1;rows=[]
    with mujoco.Renderer(model,height=240,width=320) as renderer:
        for index,q in enumerate(states):
            data.qpos[:]=q;mujoco.mj_forward(model,data);renderer.update_scene(data,camera='reuse_rgbd',scene_option=option)
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=False;renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SKYBOX]=False
            render_rgbd(renderer,model,False);render_rgbd(renderer,model,True)
            times={False:[],True:[]};outputs={}
            for _ in range(12):
                for single in (False,True):
                    start=time.perf_counter();outputs[single]=render_rgbd(renderer,model,single);times[single].append(time.perf_counter()-start)
            np.testing.assert_array_equal(outputs[False][0],outputs[True][0])
            error=float(np.max(abs(outputs[False][1]-outputs[True][1])))
            assert np.allclose(outputs[False][1],outputs[True][1],atol=1e-4,rtol=1e-4)
            rows.append(dict(state=index,native_two_pass_median_s=float(np.median(times[False])),single_pass_median_s=float(np.median(times[True])),
                             native_max_s=max(times[False]),single_max_s=max(times[True]),maximum_depth_difference_m=error,rgb_identical=True))
    report=dict(result='PASS',scope='render-only fixed snapshots; no motion/physical grasp',mujoco=mujoco.__version__,skybox=False,rows=rows)
    Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
