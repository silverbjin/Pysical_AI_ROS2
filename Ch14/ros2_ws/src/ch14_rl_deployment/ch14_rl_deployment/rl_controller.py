"""G08 T19: Ch12 control loop with the exact G07 ONNX actor and strict G07 input envelope."""
import json
import time

import numpy as np
import rclpy
from rclpy.clock import Clock,ClockType
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu,JointState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist,Point
from std_msgs.msg import Float64,String
from std_srvs.srv import Trigger
from visualization_msgs.msg import Marker

from .policy import OnnxPolicy
from .observation_adapter import ObservationAdapter


def stamp_seconds(stamp):
    return stamp.sec+stamp.nanosec*1e-9


class RLController(Node):
    def __init__(self):
        super().__init__('rl_controller')
        defaults=dict(onnx_path='',contract_path='',contract_sha256='',backend='mujoco',
            enabled=False,imu_topic='/imu/data_raw',joint_topic='/joint_states',
            odom_topic='/simulation/odom',cmd_topic='/cmd_vel',velocity_frame='body',
            sensor_timeout=.25,command_timeout=.5,max_sensor_skew=.1,
            max_target_delta=.1,startup_velocity=1.,max_inference_seconds=.02,minimum_base_height=.2)
        for name,value in defaults.items():self.declare_parameter(name,value)
        self.cfg={name:self.get_parameter(name).value for name in defaults}
        if self.cfg['backend'] not in ('mujoco','gazebo'):raise ValueError('Unknown backend')
        if self.cfg['startup_velocity']<=0 or self.cfg['max_inference_seconds']<=0:
            raise ValueError('Startup velocity and inference budget must be positive')
        self.model=OnnxPolicy(self.cfg['onnx_path'],self.cfg['contract_path'],self.cfg['contract_sha256'])
        c=self.model.contract
        if c['policy_scope']!='SMOKE_ONLY' or c['onnx_sha256']!='c6bc846346ea156f39b31a84da3e2051e17d377b39b825eb08ba3ef77f51e546' or self.cfg['contract_sha256']!='1209b04f0d6f31d12249b7fd355ba4ed7d45789cfee8d94486d869608c48d168':
            raise ValueError('G08 accepts only the pinned G07 smoke actor')
        expected=dict(sensor_timeout=.25,command_timeout=.5,max_sensor_skew=.1,
                      max_target_delta=.1,startup_velocity=1.,max_inference_seconds=.02,
                      minimum_base_height=.2,velocity_frame='body')
        if any(self.cfg[k]!=v for k,v in expected.items()):
            raise ValueError('G08 safety contract override rejected')
        self.adapter=ObservationAdapter(c)
        self.core=self.adapter.core
        self.contract=self.core.contract
        self.model.predict(np.zeros(48,dtype=np.float32),deterministic=True) # CPU warmup
        self.wall_received=self.adapter.wall
        self.faults=self.adapter.faults
        self.fault_reasons=self.adapter.faults
        self.armed=False
        self.last_height=0.
        self.startup_target=None
        self.last_clock=None
        self.startup_start=time.monotonic()
        self.inferences=0
        self.published=0
        self.overruns=0
        self.conflict=False
        self.last_graph_check=0.
        self.status_pub=self.create_publisher(String,'/rl/controller_status',10)
        self.marker_pub=self.create_publisher(Marker,'/rl/command_marker',10)
        self.targets_pub=self.create_publisher(JointState,'/rl/joint_targets',10) if self.cfg['enabled'] and self.cfg['backend']=='mujoco' else None
        self.joint_publishers={name:self.create_publisher(Float64,
            f'/model/my_quadruped/joint/{name}/cmd_pos',10) for name in self.contract.joint_names
            } if self.cfg['enabled'] and self.cfg['backend']=='gazebo' else {}
        self.create_subscription(Imu,self.cfg['imu_topic'],self.imu_callback,qos_profile_sensor_data)
        self.create_subscription(JointState,self.cfg['joint_topic'],self.joint_callback,qos_profile_sensor_data)
        self.create_subscription(Odometry,self.cfg['odom_topic'],self.odom_callback,qos_profile_sensor_data)
        self.create_subscription(Twist,self.cfg['cmd_topic'],self.command_callback,10)
        self.create_service(Trigger,'/rl/rearm',self.rearm)
        self.timer=self.create_timer(self.contract.dt,self.control_loop)
        self.watchdog=self.create_timer(.05,self.wall_watchdog,clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.get_logger().info(f"Pinned ONNX SMOKE_ONLY ready: dt={self.contract.dt}, enabled={self.cfg['enabled']}")

    def _receive(self,name,msg):
        now=self.get_clock().now().nanoseconds*1e-9
        ok=self.adapter.receive(name,msg,now)
        if ok and name=='velocity':
            self.last_height=msg.pose.pose.position.z
            if self.armed and self.last_height<self.cfg['minimum_base_height']:
                self.faults[name]='Simulation body height below deployment threshold'

    def imu_callback(self,msg):self._receive('imu',msg)
    def joint_callback(self,msg):self._receive('joints',msg)
    def odom_callback(self,msg):self._receive('velocity',msg)
    def command_callback(self,msg):self._receive('command',msg)

    def rearm(self,request,response):
        if self._writer_conflict():
            response.success=False;response.message='Command writer conflict';return response
        self.armed=False;self.startup_target=None;self.startup_start=time.monotonic()
        response.success=True;response.message='Startup ramp requested; fresh valid sensors required'
        return response

    def _publish_target(self,target):
        if not self.cfg['enabled'] or self._writer_conflict():return
        msg=JointState();msg.header.stamp=self.get_clock().now().to_msg()
        msg.name=list(self.contract.joint_names);msg.position=np.asarray(target).tolist()
        if self.cfg['backend']=='mujoco':self.targets_pub.publish(msg)
        else:
            for name,value in zip(self.contract.joint_names,target):
                out=Float64();out.data=float(value);self.joint_publishers[name].publish(out)
        self.published+=1

    def _report(self,status,obs=None,seconds=0.):
        out=String();out.data=json.dumps(dict(status=status,enabled=self.cfg['enabled'],
            sim_time=self.get_clock().now().nanoseconds*1e-9,inferences=self.inferences,
            published=self.published,overruns=self.overruns,inference_seconds=seconds,
            observation=None if obs is None else obs.tolist(),target=self.core.last_target.tolist(),
            applied_action=self.core.last_action.tolist(),faults=sorted(self.faults),fault_reasons=self.fault_reasons))
        self.status_pub.publish(out)

    def _writer_conflict(self):
        if not self.cfg['enabled']:return False
        topics=([f'/model/my_quadruped/joint/{name}/cmd_pos' for name in self.joint_publishers]
                if self.joint_publishers else ['/rl/joint_targets'])
        # Exact one discovered writer per topic; duplicate same-name nodes also fail.
        self.conflict=any(len(self.get_publishers_info_by_topic(topic))!=1 or
            any(info.node_name!=self.get_name() or info.node_namespace!=self.get_namespace()
                for info in self.get_publishers_info_by_topic(topic)) for topic in topics)
        return self.conflict

    def wall_watchdog(self):
        now=time.monotonic()
        self._writer_conflict()
        if any(now-self.wall_received.get(name,-np.inf)>.5 for name in ('imu','joints','velocity')):
            if self.published:self._publish_target(self.core.last_target)
            self._report('wall_sensor_timeout')

    def control_loop(self):
        now=self.get_clock().now().nanoseconds*1e-9
        if self.last_clock is not None and now<self.last_clock-.001:
            self.adapter.reset()
            self.armed=False;self.startup_target=None
            self.startup_start=time.monotonic()
        self.last_clock=now
        try:
            if self._writer_conflict():raise RuntimeError('Multiple or missing command publishers')
            obs=self.adapter.observation(now)
        except RuntimeError as error:
            if self.published:self._publish_target(self.core.last_target)
            self._report(str(error));return
        if not self.cfg['enabled']:
            # No actuator publisher in disabled mode. Real inference is evaluated in G07 Shadow.
            self._report('dry_run',obs);return
        if not self.armed:
            if time.monotonic()-self.startup_start>15:
                self._publish_target(self.core.last_target)
                self._report('startup_timeout',obs);return
            if self.startup_target is None:self.startup_target=self.core.positions.copy()
            delta=self.cfg['startup_velocity']*self.contract.dt
            self.startup_target+=np.clip(self.contract.nominal-self.startup_target,-delta,delta)
            self.core.sync_target(self.startup_target)
            self._publish_target(self.core.last_target)
            if (np.max(np.abs(self.core.positions-self.contract.nominal))<.12
                    and np.max(np.abs(self.core.velocities))<2
                    and self.last_height>=self.cfg['minimum_base_height']):
                self.armed=True
            self._report('arming',obs);return
        start=time.monotonic()
        try:
            action,_=self.model.predict(obs,deterministic=True)
            elapsed=time.monotonic()-start
            if elapsed>self.cfg['max_inference_seconds']:
                self.overruns+=1;self._report('inference_overrun',obs,elapsed);return
            if self._writer_conflict():
                self._report('Multiple or missing command publishers',obs);return
            target,_=self.core.process_action(action)
        except (ValueError,FloatingPointError,RuntimeError):
            self._report('invalid_inference',obs);return
        self.inferences+=1
        self._publish_target(target)
        self._report('active',obs,elapsed)
        if self.inferences%5==0:
            marker=Marker();marker.header.frame_id='base_link';marker.header.stamp=self.get_clock().now().to_msg()
            marker.ns='command';marker.id=0;marker.type=Marker.ARROW;marker.action=Marker.ADD
            marker.scale.x=.02;marker.scale.y=.04;marker.scale.z=.04
            marker.color.g=1.;marker.color.a=1.
            marker.points=[Point(x=0.,y=0.,z=.3),Point(x=float(obs[9]),y=float(obs[10]),z=.3)]
            self.marker_pub.publish(marker)


def main(args=None):
    rclpy.init(args=args);node=None
    try:
        node=RLController();rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        if node is not None:node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main()
