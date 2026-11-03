"""Bounded immutable snapshots; GL and its GIL stalls stay in an owned process."""
import hashlib,multiprocessing as mp,queue,threading,time,traceback
import mujoco
import numpy as np


def render_rgbd(renderer,model,single_pass=False):
 rgb=renderer.render().copy()
 if not single_pass:
  renderer.enable_depth_rendering();depth=renderer.render().copy();renderer.disable_depth_rendering()
  return rgb,depth
 if mujoco.__version__!='3.13.0':raise RuntimeError('single-frame RGB-D validated only with MuJoCo3.13.0')
 if renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SKYBOX]:raise ValueError('single-frame raw depth requires skybox disabled')
 # Read the real depth buffer left by the SAME RGB render, without another
 # geometry pass. Pinned Renderer internals are guarded by version+pixel tests.
 depth=np.empty((renderer.height,renderer.width),dtype=np.float32)
 mujoco.mjr_readPixels(None,depth,renderer._rect,renderer._mjr_context)
 near=np.float32(model.vis.map.znear*model.stat.extent);far=np.float32(model.vis.map.zfar*model.stat.extent)
 c=-(far+near)/(far-near);d=-(np.float32(2)*far*near)/(far-near)
 c=np.float32(-.5)*c-np.float32(.5);d=np.float32(-.5)*d
 depth=(d/(depth.astype(np.float64)+c)).astype(np.float32)
 if renderer._gl_context:depth=np.flipud(depth).copy()
 return rgb,depth

def put_render_result(results,item,stop,latest=False):
 dropped=0
 while not stop.is_set():
  try:results.put(item,timeout=.001 if latest else .05);return dropped
  except queue.Full:
   if latest:
    try:results.get_nowait();dropped+=1
    except queue.Empty:pass
 return dropped

def render_process(model,initial_q,requests,results,ready,stop,latest=False,output_dropped=None,capture_ledger=None):
 renderer=None;node=None;publisher=None;captures=[];failure='';publisher_closed=False
 try:
  if latest:
   import rclpy
   from rclpy.node import Node
   from .camera_publisher import FramePublisher
   rclpy.init(args=[]);node=Node('ch13_reuse_camera_renderer');publisher=FramePublisher(node,depth=1)
  model.vis.quality.offsamples=0
  data=mujoco.MjData(model);data.qpos[:]=initial_q;mujoco.mj_forward(model,data)
  option=mujoco.MjvOption();option.geomgroup[2]=0;option.geomgroup[3]=1;option.geomgroup[5]=1
  renderer=mujoco.Renderer(model,height=240,width=320)
  def render():
   renderer.update_scene(data,camera='reuse_rgbd',scene_option=option);renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=False
   if latest:renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SKYBOX]=False
   return render_rgbd(renderer,model,single_pass=latest)
  render();ready.set()
  while not stop.is_set():
   try:q,stamp,capture_wall=requests.get(timeout=.1)
   except queue.Empty:continue
   data.qpos[:]=q;data.time=stamp/1e9;mujoco.mj_forward(model,data);rgb,depth=render()
   meta={'capture_ns':stamp,'capture_wall':capture_wall,'render_finished_wall':time.monotonic(),'rgb_sha256':hashlib.sha256(rgb.tobytes()).hexdigest()}
   if latest:meta.update(render_profile='paired_raw_RGB_depth_v1',skybox=False,mujoco_version=mujoco.__version__)
   if publisher is not None:
    meta['publisher_route']='renderer_process_DDS_v1'
    started=time.monotonic();publisher.publish(rgb,depth,meta)
    captures.append(dict(capture=dict(meta),publish_started_wall=started,publish_finished_wall=time.monotonic()))
   item=(rgb,depth,meta)
   dropped=put_render_result(results,item,stop,latest)
   if output_dropped is not None:
    with output_dropped.get_lock():output_dropped.value+=dropped
 except BaseException:
  failure=traceback.format_exc()
  try:results.put(('error',failure),timeout=.5)
  except queue.Full:pass
 finally:
  try:
   if node is not None:node.destroy_node();rclpy.try_shutdown();publisher_closed=True
  finally:
   try:
    if renderer is not None:renderer.close()
   finally:
    if capture_ledger is not None:
     import json
     from pathlib import Path
     Path(capture_ledger).write_text(json.dumps(dict(captures=captures,publisher_closed=publisher_closed,error=failure))+'\n')
    ready.set()

class CameraWorker:
 def __init__(self,model,initial_q,callback,latest=False,capture_ledger=None):
  self.callback=callback;self.condition=threading.Condition();self.latest=None;self.stopping=False;self.error='';self.overwritten=0
  self.capture_ledger=capture_ledger;self.source_captures=None
  ctx=mp.get_context('spawn');self.requests=ctx.Queue(maxsize=1);self.results=ctx.Queue(maxsize=1 if latest else 2);self.ready=ctx.Event();self.stop=ctx.Event();self.output_dropped=ctx.Value('i',0)
  self.process=ctx.Process(target=render_process,args=(model,initial_q.copy(),self.requests,self.results,self.ready,self.stop,latest,self.output_dropped,str(capture_ledger) if capture_ledger is not None else None),name='reuse_rgbd_renderer')
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
  if self.capture_ledger is not None:
   import json
   from pathlib import Path
   try:
    ledger=json.loads(Path(self.capture_ledger).read_text());self.source_captures=[r['capture'] for r in ledger['captures']]
    if ledger['error'] or not ledger['publisher_closed']:self.error=self.error or ledger['error'] or 'renderer DDS owner failed shutdown'
   except (OSError,ValueError,KeyError):self.error=self.error or 'renderer source capture ledger unavailable'
  # A failed forced cleanup is never reported as normal camera shutdown.
  joined=not self.process.is_alive() and not self.thread.is_alive() and self.process.exitcode==0 and not self.error
  self.requests.close();self.requests.join_thread();self.results.close();self.results.join_thread();return joined
