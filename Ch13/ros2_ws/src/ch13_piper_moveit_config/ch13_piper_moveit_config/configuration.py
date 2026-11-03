"""Parameters for the installed Jazzy MoveGroup service/action interface."""
from pathlib import Path
import yaml
from ament_index_python.packages import get_package_share_directory


def parameters():
    folder=Path(get_package_share_directory('ch13_piper_moveit_config'))/'config'
    urdf=(folder/'robot.urdf').read_text();srdf=(folder/'robot.srdf').read_text()
    names=['joint'+str(i) for i in range(1,7)]
    arm='ch13/reuse/manipulation/arm_controller'
    grip='ch13/reuse/manipulation/gripper_controller'
    ompl=yaml.safe_load((folder/'ompl_planning.yaml').read_text())
    return dict(
        use_sim_time=True,robot_description=urdf,robot_description_semantic=srdf,
        robot_description_kinematics=dict(manipulator_arm=dict(
            kinematics_solver='trac_ik_kinematics_plugin/TRAC_IKKinematicsPlugin',
            kinematics_solver_timeout=.05,kinematics_solver_search_resolution=.005,solve_type='Distance')),
        robot_description_planning=dict(joint_limits={j:dict(has_velocity_limits=True,max_velocity=.5,
            has_acceleration_limits=True,max_acceleration=1.) for j in names}),
        planning_pipelines=['ompl'],default_planning_pipeline='ompl',ompl=ompl,
        allow_trajectory_execution=True,moveit_manage_controllers=False,
        moveit_controller_manager='moveit_simple_controller_manager/MoveItSimpleControllerManager',
        moveit_simple_controller_manager={'controller_names':[arm,grip],
            arm:dict(type='FollowJointTrajectory',action_ns='follow_joint_trajectory',default=True,joints=names),
            grip:dict(type='GripperCommand',action_ns='gripper_cmd',default=True,joints=['joint7'],command_joint='joint7')},
        trajectory_execution=dict(allowed_execution_duration_scaling=2.,allowed_goal_duration_margin=2.,allowed_start_tolerance=.025),
        publish_planning_scene=True,publish_geometry_updates=True,publish_state_updates=True,publish_transforms_updates=True)
