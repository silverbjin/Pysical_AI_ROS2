"""Bounded immutable snapshots; GL and its GIL stalls stay in an owned process."""
import hashlib,multiprocessing as mp,queue,threading,time,traceback
import mujoco
import numpy as np


def camera_scene_option(sensor=False):
 option=mujoco.MjvOption();option.geomgroup[2]=0;option.geomgroup[3]=1;option.geomgroup[5]=1
 # Sites are visualization markers, not physical surfaces. Keep legacy views
 # unchanged; the paired sensor stream must not see the red attachment site.
 if sensor:option.sitegroup[:]=0
 return option


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

def render_process(model,initial_q,requests,results,ready,stop,latest=False,output_dropped=None,capture_ledger=None,startup=None):
 renderer=None;node=None;publisher=None;captures=[];failure='';publisher_closed=False
 stages=[]
 def stage(event,error=None):
  row=dict(event=event,wall=time.monotonic(),cpu=time.process_time())
  if error is not None:row['error']=error
  stages.append(row)
  if startup is not None:startup.send(row)
 try:
  stage('target_enter')
  if latest:
   stage('ros_import_begin')
   import rclpy
   from rclpy.node import Node
   from .camera_publisher import FramePublisher
   stage('ros_import_end');stage('ros_init_begin');rclpy.init(args=[]);stage('ros_init_end')
   stage('node_begin');node=Node('ch13_reuse_camera_renderer');stage('node_end')
   stage('publishers_begin');publisher=FramePublisher(node,depth=1);stage('publishers_end')
  model.vis.quality.offsamples=0
  data=mujoco.MjData(model);data.qpos[:]=initial_q;mujoco.mj_forward(model,data)
  option=camera_scene_option(sensor=latest)
  stage('renderer_begin');renderer=mujoco.Renderer(model,height=240,width=320);stage('renderer_end')
  def render():
   renderer.update_scene(data,camera='reuse_rgbd',scene_option=option);renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=False
   if latest:renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SKYBOX]=False
   return render_rgbd(renderer,model,single_pass=latest)
  stage('first_render_begin');render();stage('first_render_end');stage('ready');ready.set()
  if startup is not None:startup.close();startup=None
  while not stop.is_set():
   try:q,stamp,capture_wall=requests.get(timeout=.1)
   except queue.Empty:continue
   render_started=time.monotonic();render_cpu=time.process_time()
   data.qpos[:]=q;data.time=stamp/1e9;mujoco.mj_forward(model,data);rgb,depth=render()
   meta={'capture_ns':stamp,'capture_wall':capture_wall,'render_finished_wall':time.monotonic(),'rgb_sha256':hashlib.sha256(rgb.tobytes()).hexdigest()}
   if latest:meta.update(render_profile='paired_raw_RGB_depth_v1',skybox=False,mujoco_version=mujoco.__version__,
       render_started_wall=render_started,render_elapsed_cpu_s=time.process_time()-render_cpu)
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
  if startup is not None:
   try:stage('error',failure)
   except (OSError,EOFError):pass
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
     Path(capture_ledger).write_text(json.dumps(dict(captures=captures,publisher_closed=publisher_closed,error=failure,startup=stages))+'\n')
    if startup is not None:startup.close()

class CameraWorker:
 def __init__(self,model,initial_q,callback,latest=False,capture_ledger=None):
  self.callback=callback;self.condition=threading.Condition();self.latest=None;self.stopping=False;self.error='';self.overwritten=0
  self.capture_ledger=capture_ledger;self.source_captures=None
  ctx=mp.get_context('spawn');self.requests=ctx.Queue(maxsize=1);self.results=ctx.Queue(maxsize=1 if latest else 2);self.ready=ctx.Event();self.stop=ctx.Event();self.output_dropped=ctx.Value('i',0)
  startup_rx,startup_tx=ctx.Pipe(duplex=False)
  self.startup_profile=dict(parent_start_wall=time.monotonic(),events=[])
  self.process=ctx.Process(target=render_process,args=(model,initial_q.copy(),self.requests,self.results,self.ready,self.stop,latest,self.output_dropped,str(capture_ledger) if capture_ledger is not None else None,startup_tx),name='reuse_rgbd_renderer')
  self.process.start();self.worker_pid=self.process.pid
  startup_tx.close();self.startup_profile['parent_spawned_wall']=time.monotonic()
  from multiprocessing import resource_tracker
  self.tracker_pid=resource_tracker._resource_tracker._pid
  self.thread=threading.Thread(target=self.receive,name='reuse_rgbd_rx');self.thread.start()
  deadline=time.monotonic()+15.;failure=''
  try:
   while True:
    if not startup_rx.poll(max(0.,deadline-time.monotonic())):
     last=self.startup_profile['events'][-1]['event'] if self.startup_profile['events'] else 'bootstrap'
     failure='camera process warmup deadline at '+last;break
    try:row=startup_rx.recv()
    except EOFError:
     self.process.join(.1);failure='camera process exited before startup outcome: '+str(self.process.exitcode);break
    self.startup_profile['events'].append(row)
    if row['event']=='error':failure=row['error'];break
    if row['event']=='ready':break
  finally:startup_rx.close()
  self.startup_profile['parent_outcome_wall']=time.monotonic()
  if not failure and (not self.process.is_alive() or self.error):failure=self.error or 'camera process startup failure'
  if capture_ledger is not None:
   import json
   from pathlib import Path
   self.startup_profile['outcome']='ERROR' if failure else 'READY'
   try:Path(capture_ledger).with_name('renderer_startup.json').write_text(json.dumps(self.startup_profile,indent=2)+'\n')
   except OSError as exc:failure=failure or 'camera startup audit failed: '+str(exc)
  if failure:
   self.error=failure;self.close()
   if not self.process.is_alive() and not self.thread.is_alive():
    self.process.close()
    # A retained exception traceback retains this failed constructor's self.
    # Release owned semaphore references now, outside resource-tracker locks,
    # rather than deferring their finalizers to a later cyclic collection.
    self.requests=self.results=self.ready=self.stop=self.output_dropped=None
   error=RuntimeError(failure);error.startup_profile=self.startup_profile;raise error
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
