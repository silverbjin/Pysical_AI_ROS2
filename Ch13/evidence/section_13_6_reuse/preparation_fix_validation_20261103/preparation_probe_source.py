"""Observational fixture driver; actual renderer/DDS, no physics engine."""
import os,time,json,sys,traceback,runpy,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(os.environ['PREPARATION_TRACE_DIR'])
def note(event,**values):
    with (OUT/f'events-{os.getpid()}.jsonl').open('a') as stream:
        stream.write(json.dumps(dict(event=event,wall=time.monotonic(),cpu=time.process_time(),pid=os.getpid(),**values))+'\n')
note('module_begin')
for package in ('ch13_navigation_reuse','ch13_manipulation_reuse'):
    sys.path.insert(0,str(ROOT/'Ch13/ros2_ws/src'/package))
sys.path.append('/usr/lib/python3/dist-packages')
import mujoco
note('mujoco_imported')
from ch13_navigation_reuse import camera_worker
note('camera_worker_imported')
original_render_process=camera_worker.render_process
def traced_render_process(*args):
    note('render_target_enter')
    latest=args[6];original_node=object
    if latest:
        import rclpy,rclpy.node
        from ch13_navigation_reuse.camera_publisher import FramePublisher
        note('ros_imported')
        original_init=rclpy.init;original_node=rclpy.node.Node
        original_publisher=FramePublisher.__init__;original_publish=FramePublisher.publish
    original_renderer=mujoco.Renderer
    def init(*a,**kw):
        note('rclpy_init_begin');value=original_init(*a,**kw);note('rclpy_init_end');return value
    class Node(original_node):
        def __init__(self,*a,**kw):
            note('node_begin');super().__init__(*a,**kw);note('node_end')
    def publisher(self,*a,**kw):
        note('publishers_begin');original_publisher(self,*a,**kw);note('publishers_end')
    def publish(self,*a,**kw):
        note('dds_publish',matched_readers=self.rgb.get_subscription_count())
        return original_publish(self,*a,**kw)
    class Renderer(original_renderer):
        def __init__(self,*a,**kw):
            note('renderer_begin');super().__init__(*a,**kw);self.first=True;note('renderer_end')
        def render(self,*a,**kw):
            first=self.first
            if first:note('first_render_begin')
            value=super().render(*a,**kw)
            if first:note('first_render_end');self.first=False
            return value
    if latest:rclpy.init=init;rclpy.node.Node=Node;FramePublisher.__init__=publisher;FramePublisher.publish=publish
    mujoco.Renderer=Renderer
    try:original_render_process(*args)
    finally:note('render_target_exit')

def camera_trials():
    camera_worker.render_process=traced_render_process
    fixture=runpy.run_path(str(ROOT/'Ch13/ros2_ws/src/ch13_manipulation_reuse/test/test_camera_isolation.py'))
    for attempt in range(3):
        for latest in (False,True):
            path=OUT/f'camera-{attempt}-{latest}';path.mkdir()
            note('camera_trial_begin',attempt=attempt,latest=latest)
            try:
                fixture['test_renderer_delivery_does_not_depend_on_blocked_parent_retention'](latest,path)
                note('camera_trial_result',attempt=attempt,latest=latest,result='PASS')
            except BaseException:
                note('camera_trial_result',attempt=attempt,latest=latest,result='FAIL',error=traceback.format_exc())
                import rclpy
                rclpy.try_shutdown()

def wire_trials():
    from ch13_navigation_reuse.platform_adapter import Platform
    from ch13_navigation_reuse.wire import decode
    note('platform_imported')
    class ObservedPlatform(Platform):
        def __init__(self):
            note('platform_begin');self.last_graph=None;self.first_packet=True;self.first_monitor=True
            super().__init__();note('platform_end')
        def monitor(self):
            begin=time.monotonic()
            if self.first_monitor:note('first_monitor_begin')
            super().monitor()
            graph=dict(self.guard.counts)
            if self.first_monitor or graph!=self.last_graph or time.monotonic()-begin>.05:
                note('monitor_end',elapsed=time.monotonic()-begin,counts=graph,samples=self.guard.samples,
                     clock_ns=self.guard.clock_ns,clock_wall=self.guard.clock_wall,fault=self.guard.fault)
            self.last_graph=graph;self.first_monitor=False
        def on_packet(self,packet):
            key,msg,info=decode(packet.data);now=time.monotonic();super().on_packet(packet)
            if self.first_packet or now-info['receipt_wall']>.05 or self.guard.fault:
                note('platform_packet',key=key,native_receipt=info['receipt_wall'],clock_ns=self.guard.clock_ns,
                     clock_wall=self.guard.clock_wall,samples=self.guard.samples,fault=self.guard.fault)
            self.first_packet=False
    fixture=runpy.run_path(str(ROOT/'Ch13/ros2_ws/src/ch13_navigation_reuse/test/test_platform_wire.py'))
    cls=fixture['PlatformWireTests'];cls.setUp.__globals__['Platform']=ObservedPlatform
    for attempt in range(3):
        for name in unittest.defaultTestLoader.getTestCaseNames(cls):
            note('wire_trial_begin',attempt=attempt,name=name)
            case=cls(name);result=unittest.TestResult();case.run(result)
            if not hasattr(case,'p'):
                note('wire_setup_failure',failures=[text for _,text in result.failures+result.errors]);return
            note('wire_trial_result',attempt=attempt,name=name,result='PASS' if result.wasSuccessful() else 'FAIL',
                 failures=[text for _,text in result.failures+result.errors],
                 guard=dict(samples=case.p.guard.samples,counts=case.p.guard.counts,fault=case.p.guard.fault,
                            clock_ns=case.p.guard.clock_ns,clock_wall=case.p.guard.clock_wall))

if __name__=='__main__':
    camera_trials();wire_trials();note('all_trials_finished')
