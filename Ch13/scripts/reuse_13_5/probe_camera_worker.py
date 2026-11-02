"""Bounded renderer throughput probe; not physical/vision approach acceptance."""
from pathlib import Path
import json,time,mujoco,sys
from ch13_navigation_reuse.scene import make_model
from ch13_navigation_reuse.sensors import SensorSuite
def main():
 root=Path(__file__).resolve().parents[3];out=Path(sys.argv[1]) if len(sys.argv)>1 else root/'Ch13/evidence/section_13_5_reuse/r4_preflight/camera_component';out.mkdir(exist_ok=True);m=make_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml','vision');d=mujoco.MjData(m);d.qpos[:]=m.key_qpos[m.key('home').id];mujoco.mj_forward(m,d);s=SensorSuite(m,d,'vision',out)
 try:
  start=time.monotonic()
  for i in range(24):
   target=start+i/15.;time.sleep(max(0,target-time.monotonic()));s.request_capture(d.qpos,round((2+i/15)*1e9),time.monotonic())
  time.sleep(.2)
 finally:joined=s.close()
 latencies=[r['render_finished_wall']-r['capture_wall'] for r in s.meta];summary={'scope':'renderer component only; no physics/Nav2 PASS','frames':len(latencies),'joined':joined,'max_source_capture_age_s':max(latencies),'source_limit_s':.3,'overwritten_waiting':s.camera.overwritten,'error':s.camera.error};(out/'component_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));assert joined and not s.camera.error and len(latencies)>=12 and max(latencies)<=.3
if __name__=='__main__':main()
