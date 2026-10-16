"""11.7: bounded exploration with readiness checks, handoff and map-save job."""
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
from rclpy.time import Time
from rcl_interfaces.msg import ParameterDescriptor
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry, OccupancyGrid
from sensor_msgs.msg import Imu, LaserScan
from std_msgs.msg import String
from std_srvs.srv import SetBool, Trigger
from tf2_ros import Buffer, TransformException, TransformListener
from my_quadruped_bot.mission.exploration_core import ExplorerCore, summarize_scan
from my_quadruped_bot.mission.map_artifacts import analyze_map
from my_quadruped_bot.sensors.attitude_history import unit


class AutonomousExplorer(Node):
    def __init__(self):
        super().__init__('autonomous_explorer', parameter_overrides=[Parameter('use_sim_time', value=True)])
        desc = ParameterDescriptor(read_only=True)
        defaults = {'duration':300.0, 'linear_speed':.05, 'angular_speed':.15,
                    'obstacle_distance':.9,'clear_distance':1.05,'turn_clearance':.5,
                    'seed':42,'settle_time':5.0,'auto_save':True,
                    'output_dir':str(Path.home()/'Pysical_AI_maps')}
        for k,v in defaults.items(): self.declare_parameter(k,v,desc)
        self.options = {k:self.get_parameter(k).value for k in
                        ('duration','linear_speed','angular_speed','obstacle_distance','clear_distance','turn_clearance','seed')}
        self.core = ExplorerCore(**self.options)
        if not math.isfinite(self.get_parameter('settle_time').value) or self.get_parameter('settle_time').value < 1.0:
            raise ValueError('settle_time must be finite and at least 1 second')
        self.enabled = True
        self.inputs = {}
        self.sensors = None
        self.pose = (0,0,0)
        self.attitude_ok = False
        self.map_stats = None
        self.ready_since = None
        self.readiness_reason = 'startup'
        self.last_ros = None
        self.time_reversed = False
        self.buffer = Buffer(node=self)
        self.listener = TransformListener(self.buffer,self)
        self.cmd_pub = self.create_publisher(Twist,'/cmd_vel',10)
        self.status_pub = self.create_publisher(String,'/exploration/status',10)
        self.subscriptions_kept = [
            self.create_subscription(LaserScan,'/scan',self.raw_scan,qos_profile_sensor_data),
            self.create_subscription(LaserScan,'/scan_stabilized',self.stable_scan,qos_profile_sensor_data),
            self.create_subscription(Odometry,'/odom',self.odom,qos_profile_sensor_data),
            self.create_subscription(Imu,'/imu/data_raw',self.imu,qos_profile_sensor_data),
            self.create_subscription(OccupancyGrid,'/map',self.map,
                QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL)),
        ]
        self.enable_service = self.create_service(SetBool,'/exploration/enable',self.enable)
        self.save_service = self.create_service(Trigger,'/exploration/save_map',self.save_request)
        self.save_state = 'IDLE'
        self.save_pending = None
        self.process = None
        self.save_prefix = None
        self.save_error = None
        self.output_log = None
        self.auto_save_requested = False
        self.timer = self.create_timer(.1,self.tick,clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.status_timer = self.create_timer(1.0,self.publish_status,clock=Clock(clock_type=ClockType.STEADY_TIME))

    def touch(self,key,msg):
        self.inputs[key] = (msg.header.stamp.sec+msg.header.stamp.nanosec/1e9,time.monotonic())

    def raw_scan(self,msg):
        if msg.header.frame_id != 'lidar_link':
            self.sensors = None
            return
        self.touch('raw',msg)
        self.sensors = summarize_scan(msg.ranges,msg.angle_min,msg.angle_increment,msg.range_min,msg.range_max)

    def stable_scan(self,msg):
        if msg.header.frame_id == 'lidar_link': self.touch('stable',msg)

    def odom(self,msg):
        if (msg.header.frame_id,msg.child_frame_id) != ('odom','base_footprint'): return
        p,q=msg.pose.pose.position,msg.pose.pose.orientation
        try: x,y,z,w=unit((q.x,q.y,q.z,q.w))
        except ValueError: return
        if not all(math.isfinite(v) for v in (p.x,p.y,p.z)): return
        self.pose=(p.x,p.y,math.atan2(2*(w*z+x*y),1-2*(y*y+z*z)))
        self.height_ok = .20 <= p.z <= .60
        self.odom_stamp=msg.header.stamp
        self.touch('odom',msg)

    def imu(self,msg):
        self.attitude_ok = False
        if msg.header.frame_id != 'base_link' or msg.orientation_covariance[0] == -1: return
        q=msg.orientation
        try: x,y,_,_=unit((q.x,q.y,q.z,q.w))
        except ValueError: return
        tilt=math.acos(max(-1,min(1,1-2*(x*x+y*y))))
        self.attitude_ok = tilt <= math.radians(15)
        self.touch('imu',msg)

    def map(self,msg):
        if (msg.header.frame_id != 'map' or msg.info.width*msg.info.height != len(msg.data)
                or not math.isfinite(msg.info.resolution) or msg.info.resolution <= 0
                or msg.info.width <= 0 or msg.info.height <= 0
                or any(v < -1 or v > 100 for v in msg.data)): return
        cells=msg.data
        self.map_stats={'width':msg.info.width,'height':msg.info.height,
                        'known_cells':sum(v>=0 for v in cells),'free_cells':sum(0<=v<=25 for v in cells),
                        'occupied_cells':sum(v>=65 for v in cells)}
        self.touch('map',msg)

    def ready(self,now):
        ros=self.get_clock().now().nanoseconds/1e9
        if self.last_ros is not None and ros < self.last_ros-.001: self.time_reversed=True
        self.last_ros=ros
        if self.time_reversed:
            self.readiness_reason='clock_reset_restart_required'; return False
        for key,limit in (('raw',.4),('stable',1.2),('odom',.5),('imu',.4),('map',10.0)):
            stamp,received=self.inputs.get(key,(-math.inf,-math.inf))
            if not (-.05 <= ros-stamp <= limit and 0 <= now-received <= limit):
                self.readiness_reason=f'{key}_missing_stale_or_future'; return False
        if not self.attitude_ok or not getattr(self,'height_ok',False) or not self.sensors or not self.sensors.valid:
            self.readiness_reason='body_height_tilt_or_scan_invalid'; return False
        if not self.map_stats or not self.map_stats['free_cells'] or not self.map_stats['occupied_cells']:
            self.readiness_reason='map_has_no_free_or_occupied_cells'; return False
        try: self.buffer.lookup_transform('map','base_footprint',Time.from_msg(self.odom_stamp))
        except TransformException:
            self.readiness_reason='map_to_body_tf_unavailable'; return False
        self.readiness_reason='ready_settling_or_running'
        return True

    def enable(self,request,response):
        if self.process is not None or self.save_pending is not None:
            response.success=False; response.message='Save in progress: wait for SAVED or SAVE_FAILED before mode handoff.'
            return response
        if request.data:
            if self.time_reversed:
                response.success=False; response.message='Save in progress or clock reset: wait/restart.'
                return response
            if len(self.get_publishers_info_by_topic('/cmd_vel')) > 1:
                response.success=False; response.message='Stop other cmd_vel publishers before enabling.'
                return response
            self.core=ExplorerCore(**self.options)
            self.ready_since=None
            self.auto_save_requested=False
            self.save_state='IDLE'
            self.save_prefix=None
            self.save_error=None
        self.enabled=request.data
        self.cmd_pub.publish(Twist())
        response.success=True
        response.message='Enabled: waiting for readiness.' if request.data else 'Paused: zero sent; periodic cmd_vel publication released for teleop.'
        return response

    def save_request(self,request,response):
        if not self.enabled:
            response.success=False; response.message='Stop teleop and enable explorer before requesting a stop-and-save.'
        elif self.save_pending is not None or self.process is not None:
            response.success=False; response.message='Save already pending/running.'
        elif not self.map_stats or not self.map_stats['known_cells']:
            response.success=False; response.message='No usable map received.'
        else:
            self.core.state,self.core.reason='FINISHED','operator_requested_partial_map'
            self.request_save()
            response.success=True; response.message='Stop-and-save accepted; inspect /exploration/status for SAVED or SAVE_FAILED.'
        return response

    def request_save(self):
        self.auto_save_requested=True
        self.save_pending=time.monotonic()+1.0
        self.save_state='SAVE_PENDING'
        self.cmd_pub.publish(Twist())

    def save_tick(self,now):
        if self.save_pending is not None and now >= self.save_pending:
            self.save_pending=None
            try:
                output=Path(self.get_parameter('output_dir').value).expanduser().resolve()
                output.mkdir(parents=True,exist_ok=True)
                tag=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
                self.save_prefix=output/f'maze_result_{tag}'
                if any(self.save_prefix.with_suffix(ext).exists() for ext in ('.yaml','.pgm')):
                    raise FileExistsError('Refusing to overwrite previous map')
                self.output_log=self.save_prefix.with_suffix('.save.log').open('w')
                args=['ros2','run','nav2_map_server','map_saver_cli','-t','/map','-f',str(self.save_prefix),
                      '--fmt','pgm','--free','0.196','--occ','0.65','--ros-args','-p','use_sim_time:=true','-p','save_map_timeout:=10.0',
                      '-p','map_subscribe_transient_local:=true']
                self.process=subprocess.Popen(args,stdout=self.output_log,stderr=subprocess.STDOUT,start_new_session=True)
                self.save_deadline=now+30
                self.save_state='SAVING'
            except (OSError,ValueError) as error:
                self.save_state,self.save_error='SAVE_FAILED',str(error)
                if self.output_log: self.output_log.close()
        if self.process is not None:
            if now > self.save_deadline and self.process.poll() is None:
                try: os.killpg(self.process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                self.save_error='Map saver exceeded wall-clock timeout'
            result=self.process.poll()
            if result is not None:
                self.process=None
                self.output_log.close()
                try:
                    if result != 0: raise ValueError(f'map_saver exit {result}: inspect save log')
                    report=analyze_map(self.save_prefix.with_suffix('.yaml'))
                    if not report['pixel_counts']['free_light'] or not report['pixel_counts']['occupied_black']:
                        raise ValueError('Saved map lacks free or occupied rendered cells')
                    report.update(reason=self.core.reason,complete_coverage_verified=False,mission_state=self.core.state)
                    self.save_prefix.with_suffix('.mission.json').write_text(json.dumps(report,indent=2)+'\n')
                    self.save_state='SAVED'
                    self.save_error=None
                except (OSError,ValueError,KeyError,TypeError) as error:
                    self.save_state,self.save_error='SAVE_FAILED',str(error)

    def tick(self):
        now=time.monotonic()
        self.save_tick(now)
        if not self.enabled: return  # no competing zero stream during manual teleop
        if len(self.get_publishers_info_by_topic('/cmd_vel')) > 1:
            self.enabled=False
            self.core.reason='command_publisher_conflict_paused'
            self.cmd_pub.publish(Twist())
            self.get_logger().error('Multiple cmd_vel publishers: paused; stop other sources before enabling.')
            return
        ready=self.ready(now)
        if not ready: self.ready_since=None
        elif self.ready_since is None: self.ready_since=now
        settled=ready and now-self.ready_since >= self.get_parameter('settle_time').value
        vx,wz=self.core.step(now,settled,self.sensors,self.pose)
        command=Twist(); command.linear.x=vx; command.angular.z=wz
        self.cmd_pub.publish(command)
        if self.core.state in ('FINISHED','BLOCKED') and not self.auto_save_requested and self.get_parameter('auto_save').value:
            self.request_save()

    def publish_status(self):
        msg=String()
        msg.data=json.dumps({'state':self.core.state if self.enabled else 'PAUSED','reason':self.core.reason,
                             'save_state':self.save_state,'save_prefix':str(self.save_prefix) if self.save_prefix else None,
                             'save_error':self.save_error,'readiness':self.readiness_reason,'map':self.map_stats,'complete_coverage_verified':False})
        self.status_pub.publish(msg)

    def stop(self):
        if self.enabled and rclpy.ok(): self.cmd_pub.publish(Twist())
        if self.process is not None and self.process.poll() is None:
            try: os.killpg(self.process.pid,signal.SIGTERM)
            except ProcessLookupError: pass
        if self.output_log: self.output_log.close()


def main(args=None):
    rclpy.init(args=args)
    node=None
    try:
        node=AutonomousExplorer()
        rclpy.spin(node)
    except (KeyboardInterrupt,ExternalShutdownException): pass
    finally:
        if node is not None:
            node.stop()
            node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()


if __name__=='__main__': main()
