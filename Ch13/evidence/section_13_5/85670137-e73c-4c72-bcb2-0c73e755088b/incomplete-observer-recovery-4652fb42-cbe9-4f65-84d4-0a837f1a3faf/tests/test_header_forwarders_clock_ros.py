"""Actual DDS headers and TF remain source-captured without a local sim clock."""
import math
import time
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage
from mujoco_ros2_control_msgs.msg import FreeJointState,FreeJointStateArray
from integrated_robot_vision.native_pose import NativePoseAdapter
from integrated_robot_vision.camera_info_adapter import NativeCameraInfoAdapter


@pytest.mark.parametrize('sim_clock',[True,False])
def test_header_only_forwarders_preserve_capture_and_tf_with_no_clock_publisher(sim_clock):
    rclpy.init(args=['--ros-args','-p','engine:=mujoco','-p',f'use_sim_time:={str(sim_clock).lower()}'])
    pose=info=peer=executor=None
    try:
        pose=NativePoseAdapter();info=NativeCameraInfoAdapter()
        peer=Node('header_forwarder_peer',use_global_arguments=False)
        executor=SingleThreadedExecutor()
        for node in (pose,info,peer):executor.add_node(node)
        for node in (pose,info):
            assert sum(s.topic_name=='/clock' for s in node.subscriptions)==int(sim_clock)
        assert peer.count_publishers('/clock')==0
        native=peer.create_publisher(FreeJointStateArray,'/native/free_joint_states',10)
        calibration=peer.create_publisher(CameraInfo,'/native/camera_info',10)
        odom=[];camera=[];transforms=[]
        peer.create_subscription(Odometry,'/odom',odom.append,10)
        peer.create_subscription(CameraInfo,'/camera/color/camera_info',camera.append,10)
        peer.create_subscription(TFMessage,'/tf',lambda msg:transforms.extend(msg.transforms),10)
        state=FreeJointState(name='base_link')
        state.pose.header.stamp.sec=17;state.pose.header.stamp.nanosec=123
        state.pose.pose.position.x=.25;state.pose.pose.position.z=.46
        state.pose.pose.orientation.z=math.sqrt(.5);state.pose.pose.orientation.w=math.sqrt(.5)
        state.twist.twist.linear.x=1.;state.twist.twist.angular.z=.03
        message=CameraInfo();message.header.stamp=state.pose.header.stamp
        message.header.frame_id='camera_optical_frame';message.width=320;message.height=240
        message.distortion_model='plumb_bob';message.d=[0.]*5
        message.k=[277.,0.,160.,0.,277.,120.,0.,0.,1.]
        message.p=[277.,0.,160.,0.,0.,277.,120.,0.,0.,0.,1.,0.]
        deadline=time.monotonic()+3.
        while not (odom and camera and transforms) and time.monotonic()<deadline:
            native.publish(FreeJointStateArray(free_joints=[state]));calibration.publish(message)
            executor.spin_once(timeout_sec=.01)
        assert odom and camera and transforms
        assert odom[0].header.stamp==camera[0].header.stamp==transforms[0].header.stamp==message.header.stamp
        assert odom[0].header.frame_id==transforms[0].header.frame_id=='odom'
        assert odom[0].child_frame_id==transforms[0].child_frame_id=='base_footprint'
        assert odom[0].pose.pose==state.pose.pose
        assert odom[0].twist.twist.linear.x==pytest.approx(0.,abs=1e-12)
        assert odom[0].twist.twist.linear.y==pytest.approx(-1.)
        assert odom[0].twist.twist.angular.z==.03
        assert camera[0].header==message.header and list(camera[0].k)==list(message.k)
        assert list(camera[0].r)==[1.,0.,0.,0.,1.,0.,0.,0.,1.]
        assert peer.count_publishers('/odom')==1
    finally:
        if executor is not None:executor.shutdown(timeout_sec=2.)
        for node in (pose,info,peer):
            if node is not None:node.destroy_node()
        rclpy.try_shutdown()
