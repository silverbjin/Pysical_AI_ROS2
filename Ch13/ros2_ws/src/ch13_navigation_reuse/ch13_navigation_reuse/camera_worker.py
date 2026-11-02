"""Bounded immutable snapshots; GL and its GIL stalls stay in an owned process."""
import hashlib,multiprocessing as mp,queue,threading,time,traceback
import mujoco

def render_process(model,initial_q,requests,results,ready,stop):
 renderer=None
 try:
  model.vis.quality.offsamples=0
  data=mujoco.MjData(model);data.qpos[:]=initial_q;mujoco.mj_forward(model,data)
  option=mujoco.MjvOption();option.geomgroup[2]=0;option.geomgroup[3]=1;option.geomgroup[5]=1
  renderer=mujoco.Renderer(model,height=240,width=320)
  def render():
   renderer.update_scene(data,camera='reuse_rgbd',scene_option=option);renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=False
   rgb=renderer.render().copy();renderer.enable_depth_rendering();depth=renderer.render().copy();renderer.disable_depth_rendering();return rgb,depth
  render();ready.set()
  while not stop.is_set():
   try:q,stamp,capture_wall=requests.get(timeout=.1)
   except queue.Empty:continue
   data.qpos[:]=q;data.time=stamp/1e9;mujoco.mj_forward(model,data);rgb,depth=render()
   item=(rgb,depth,{'capture_ns':stamp,'capture_wall':capture_wall,'render_finished_wall':time.monotonic(),'rgb_sha256':hashlib.sha256(rgb.tobytes()).hexdigest()})
   while not stop.is_set():
    try:results.put(item,timeout=.05);break
    except queue.Full:continue
 except BaseException:
  try:results.put(('error',traceback.format_exc()),timeout=.5)
  except queue.Full:pass
 finally:
  if renderer is not None:renderer.close()
  ready.set()

class CameraWorker:
 def __init__(self,model,initial_q,callback):
  self.callback=callback;self.condition=threading.Condition();self.latest=None;self.stopping=False;self.error='';self.overwritten=0
  ctx=mp.get_context('spawn');self.requests=ctx.Queue(maxsize=1);self.results=ctx.Queue(maxsize=2);self.ready=ctx.Event();self.stop=ctx.Event()
  self.process=ctx.Process(target=render_process,args=(model,initial_q.copy(),self.requests,self.results,self.ready,self.stop),name='reuse_rgbd_renderer')
  self.process.start();self.worker_pid=self.process.pid
  from multiprocessing import resource_tracker
  self.tracker_pid=resource_tracker._resource_tracker._pid
  self.thread=threading.Thread(target=self.receive,name='reuse_rgbd_rx');self.thread.start()
  if not self.ready.wait(15.):self.close();raise RuntimeError('camera process warmup deadline')
  if not self.process.is_alive() or self.error:self.close();raise RuntimeError(self.error or 'camera process startup failure')
 def offer(self,q,stamp,capture_wall):
  if self.stopping or self.error:return False
  item=(q.copy(),stamp,capture_wall)
  try:self.requests.put_nowait(item);return True
  except queue.Full:
   self.overwritten+=1
   try:self.requests.get_nowait()
   except queue.Empty:return False
   try:self.requests.put_nowait(item);return True
   except queue.Full:return False
 def get(self,stamp,timeout):
  with self.condition:
   if not self.condition.wait_for(lambda:self.error or (self.latest is not None and self.latest[2]['capture_ns']>=stamp),timeout):raise TimeoutError('camera snapshot deadline')
   if self.error:raise RuntimeError(self.error)
   rgb,depth,meta=self.latest;return rgb.copy(),depth.copy(),dict(meta)
 def receive(self):
  try:
   while True:
    try:item=self.results.get(timeout=.1)
    except queue.Empty:
     if not self.process.is_alive():break
     continue
    if isinstance(item[0],str):raise RuntimeError(item[1])
    rgb,depth,meta=item;self.callback(rgb,depth,meta)
    with self.condition:self.latest=item;self.condition.notify_all()
  except BaseException:
   with self.condition:self.error=traceback.format_exc();self.condition.notify_all()
 def close(self,timeout=5.):
  self.stopping=True;self.stop.set();self.process.join(timeout)
  if self.process.is_alive():
   self.error=self.error or 'camera process did not stop normally';self.process.terminate();self.process.join(2.)
  self.thread.join(2.)
  # A failed forced cleanup is never reported as normal camera shutdown.
  joined=not self.process.is_alive() and not self.thread.is_alive() and self.process.exitcode==0 and not self.error
  self.requests.close();self.requests.join_thread();self.results.close();self.results.join_thread();return joined
