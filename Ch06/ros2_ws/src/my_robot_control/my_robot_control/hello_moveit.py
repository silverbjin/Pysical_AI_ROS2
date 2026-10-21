"""Ch06 MoveItPy example: plan a named pose and a position-only IK goal.

Safe default is PLAN ONLY. --execute opts in to mock/Gazebo controller execution.
Never connect to real hardware without separate safety verification.
"""
import argparse
from pathlib import Path

import rclpy
from geometry_msgs.msg import PoseStamped
from moveit.planning import MoveItPy
from moveit_configs_utils import MoveItConfigsBuilder
from ament_index_python.packages import get_package_share_directory


def build_moveit_config():
    # This file is installed by my_robot_description, unlike the missing
    # my_robot_moveit_config/urdf/my_robot.urdf referenced by the old demo.
    description = Path(get_package_share_directory("my_robot_description"))
    urdf = description / "urdf" / "my_robot.urdf.xacro"
    if not urdf.is_file():
        raise FileNotFoundError(f"Robot model not installed: {urdf}")
    moveit_config = (
        MoveItConfigsBuilder(robot_name="my_robot", package_name="my_robot_moveit_config")
        .robot_description(file_path=str(urdf))
        .robot_description_semantic(file_path="config/my_robot.srdf")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .joint_limits(file_path="config/joint_limits.yaml")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"], default_planning_pipeline="ompl")
        .to_moveit_configs()
    )
    params = moveit_config.to_dict()
    kin = params.get("robot_description_kinematics", {})
    if "arm_group" in kin:
        # Five arm joints cannot in general satisfy an arbitrary 6D pose.
        kin["arm_group"]["position_only_ik"] = True
    # MoveItPy's MoveItCpp expects its own pipeline naming and scene monitor.
    planning = params.get("planning_pipelines", {})
    ompl = planning.get("ompl") if isinstance(planning, dict) else None
    if ompl is None:
        raise RuntimeError("OMPL configuration not loaded")
    params["ompl"] = ompl
    params["planning_pipelines"] = {
        "pipeline_names": ["ompl"],
        "default_planning_pipeline": "ompl",
    }
    params["planning_scene_monitor_options"] = {
        "name": "planning_scene_monitor",
        "robot_description": "robot_description",
        "joint_state_topic": "/joint_states",
        "wait_for_initial_state_timeout": 10.0,
    }
    params["plan_request_params"] = {
        "planning_pipeline": "ompl", "planner_id": "RRTConnectkConfigDefault",
        "planning_attempts": 1, "planning_time": 5.0,
        "max_velocity_scaling_factor": 0.2,
        "max_acceleration_scaling_factor": 0.2,
    }
    return params


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="opt in to trajectory execution")
    parser.add_argument("--target", nargs=3, type=float, default=[0.3, 0.0, 1.1],
                        metavar=("X", "Y", "Z"), help="IK target in base_link [metres]")
    parser.add_argument("--named", default="ready", help="SRDF named configuration")
    return parser.parse_args(argv)


def plan_step(robot, component, label, goal, execute=False):
    component.set_start_state_to_current_state()
    goal(component)
    plan = component.plan()
    if not plan:
        print(f"FAIL: {label} PLANNING (check collision, IK and scene state)")
        return False
    print(f"PASS: {label} PLAN ONLY (not an execution or goal-reach result)")
    if execute:
        result = robot.execute(plan.trajectory, controllers=[])
        print(f"EXECUTION RESULT for {label}: {result!s}")
        # Never announce a task success without controller/feedback evidence.
        if "SUCCEEDED" not in str(result).upper():
            print("UNVERIFIED: check FollowJointTrajectory action result and final FK")
            return False
    return True


def main():
    args = parse_arguments()
    rclpy.init()
    try:
        config = build_moveit_config()
        robot = MoveItPy(node_name="hello_moveit", config_dict=config)
        arm = robot.get_planning_component("arm_group")
        print("MODE:", "EXECUTE (sim/mock only)" if args.execute else "PLAN ONLY")
        if not plan_step(robot, arm, "named", lambda a: a.set_goal_state(
                configuration_name=args.named), args.execute):
            return 1
        goal = PoseStamped()
        goal.header.frame_id = "base_link"
        goal.pose.position.x, goal.pose.position.y, goal.pose.position.z = args.target
        goal.pose.orientation.w = 1.0  # ignored by position_only_ik; explicitly documented
        if not plan_step(robot, arm, "IK XYZ", lambda a: a.set_goal_state(
                pose_stamped_msg=goal, pose_link="link_wrist"), args.execute):
            return 2
        return 0
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"SETUP FAILED: {error}")
        return 3
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
