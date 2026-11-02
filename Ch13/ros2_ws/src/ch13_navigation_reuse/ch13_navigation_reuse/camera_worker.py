"""Single-slot immutable snapshots; renderer/context lifetime stays on one worker."""
import hashlib,threading,time,traceback
import numpy as np,mujoco
class CameraWorker:
 def __init__(self,model,initial_q,callback):
  self.model=model;self.initial_q=initial_q.copy();self.callback=callback;self.condition=threading.Condition();self.slot=None;self.latest=None;self.stopping=False;self.error='';self.ready=threading.Event();self.overwritten=0
  model.vis.quality.offsamples=0 # visual only; fixed320x240 geometry/depth calibration unchanged
  self.thread=threading.Thread(target=self.run,name='reuse_rgbd_renderer');self.thread.start()
  if not self.ready.wait(10.):raise RuntimeError('camera worker warmup deadline')
  if self.error:raise RuntimeError(self.error)
 def offer(self,q,stamp,capture_wall):
  with self.condition:
   if self.stopping or self.error:return False
   if self.slot is not None:self.overwritten+=1
   self.slot=(q.copy(),stamp,capture_wall);self.condition.notify_all();return True
 def get(self,stamp,timeout):
  with self.condition:
   if not self.condition.wait_for(lambda:self.error or (self.latest is not None and self.latest[2]['capture_ns']>=stamp),timeout):raise TimeoutError('camera snapshot deadline')
   if self.error:raise RuntimeError(self.error)
   rgb,depth,meta=self.latest;return rgb.copy(),depth.copy(),dict(meta)
 def render(self,renderer,data,option):
  renderer.update_scene(data,camera='reuse_rgbd',scene_option=option);renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=False
  rgb=renderer.render().copy();renderer.enable_depth_rendering();depth=renderer.render().copy();renderer.disable_depth_rendering();return rgb,depth
 def run(self):
  renderer=None
  try:
   data=mujoco.MjData(self.model);data.qpos[:]=self.initial_q;mujoco.mj_forward(self.model,data);option=mujoco.MjvOption();option.geomgroup[2]=0;option.geomgroup[3]=1;option.geomgroup[5]=1;renderer=mujoco.Renderer(self.model,height=240,width=320);self.render(renderer,data,option);self.ready.set()
   while True:
    with self.condition:
     self.condition.wait_for(lambda:self.stopping or self.slot is not None)
     if self.stopping:break
     q,stamp,capture_wall=self.slot;self.slot=None
    data.qpos[:]=q;data.time=stamp/1e9;mujoco.mj_forward(self.model,data);rgb,depth=self.render(renderer,data,option);meta={'capture_ns':stamp,'capture_wall':capture_wall,'render_finished_wall':time.monotonic(),'rgb_sha256':hashlib.sha256(rgb.tobytes()).hexdigest()};self.callback(rgb,depth,meta)
    with self.condition:self.latest=(rgb,depth,meta);self.condition.notify_all()
  except BaseException:
   with self.condition:self.error=traceback.format_exc();self.condition.notify_all()
  finally:
   if renderer is not None:renderer.close()
   self.ready.set()
 def close(self,timeout=2.):
  with self.condition:self.stopping=True;self.slot=None;self.condition.notify_all()
  self.thread.join(timeout);return not self.thread.is_alive()
