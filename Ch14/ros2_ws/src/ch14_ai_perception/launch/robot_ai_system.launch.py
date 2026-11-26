"""Installed YAML profile, explicit typed launch overrides, actual replay or Gazebo sensor input."""
from pathlib import Path
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,OpaqueFunction,ExecuteProcess,SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ch14_ai_perception.parameters import DEFAULTS,validate_startup

KEYS=tuple(k for k in DEFAULTS if k!="onnx")+("use_sim_time",)
def convert(k,s):
    default=False if k=="use_sim_time" else DEFAULTS[k]
    if type(default) is bool:
        if s not in ("true","false"):raise ValueError(k+" must be true/false")
        return s=="true"
    if type(default) is int:return int(s)
    if type(default) is float:return float(s)
    return s

def assemble(context):
    arg=lambda k:LaunchConfiguration(k).perform(context)
    profile=arg("profile")
    if profile not in ("sim","replay"):raise ValueError("unknown profile")
    share=Path(get_package_share_directory("ch14_ai_perception"))
    config=Path(arg("config")) if arg("config") else share/"config"/("params_"+profile+".yaml")
    if not config.is_absolute() or not config.is_file():raise ValueError("absolute existing YAML required")
    values=yaml.safe_load(config.read_text())["/**"]["ros__parameters"]
    if not isinstance(values,dict) or set(values)-set(KEYS):raise ValueError("unknown YAML parameter")
    overrides={k:convert(k,arg(k)) for k in KEYS if arg(k)!=""}
    p=dict(DEFAULTS,use_sim_time=False,**{}) ;p.update(values);p.update(overrides)
    if type(p["use_sim_time"]) is not bool:raise ValueError("use_sim_time type")
    p=validate_startup(p)
    if not Path(p["onnx"]).is_file():raise ValueError("model file missing")
    if p["model_registry"] and not Path(p["model_registry"]).is_file():raise ValueError("registry file missing")
    actions=[]
    if profile=="sim":
        if not p["rgbd"] or not p["use_sim_time"]:raise ValueError("sim requires rgbd and use_sim_time")
        assets=Path(arg("assets"))
        if not assets.is_absolute() or not (assets/"person_standing/model.sdf").is_file():raise ValueError("verified scene assets required")
        world=Path(get_package_share_directory("ch14_simulation"))/"worlds/semantic_rgbd.sdf"
        gui=arg("gui")
        if gui not in ("true","false"):raise ValueError("gui must be true/false")
        gz=["gz","sim","-r",str(world)] if gui=="true" else ["gz","sim","-s","-r","--headless-rendering",str(world)]
        actions.extend([
            SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH",str(assets)),
            ExecuteProcess(cmd=gz,output="screen"),
            Node(package="ros_gz_bridge",executable="parameter_bridge",arguments=[
                "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
                "/ch14/rgbd/image@sensor_msgs/msg/Image[gz.msgs.Image",
                "/ch14/rgbd/depth_image@sensor_msgs/msg/Image[gz.msgs.Image",
                "/ch14/rgbd/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo"],
                parameters=[{"override_frame_id":"camera_optical"}],
                remappings=[("/ch14/rgbd/image",p["input_topic"]),
                    ("/ch14/rgbd/depth_image","/camera/aligned_depth_to_color/image_raw"),
                    ("/ch14/rgbd/camera_info","/camera/color/camera_info")],output="screen"),
            Node(package="tf2_ros",executable="static_transform_publisher",arguments=[
                "--x","0","--y","0","--z","1","--roll","-1.5707963267948966","--pitch","0","--yaw","-1.5707963267948966","--frame-id","odom","--child-frame-id","camera_optical"],output="screen")])
    actions.append(Node(package="ch14_ai_perception",executable="detector_node",name="yolo_detector_node",
                        parameters=[str(config),overrides],output="screen"))
    return actions

def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument("profile",default_value="replay"),
        DeclareLaunchArgument("config",default_value=""),
        DeclareLaunchArgument("assets",default_value=""),
        DeclareLaunchArgument("gui",default_value="false"),
        *(DeclareLaunchArgument(k,default_value="") for k in KEYS),OpaqueFunction(function=assemble)])
