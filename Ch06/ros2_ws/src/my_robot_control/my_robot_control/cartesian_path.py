"""Cartesian LIN segment example for Ch06 (plan-only by default).

Unlike compute_cartesian_path(...), this uses the Pilz LIN motion planner.
Each segment is planned independently; a 5-DOF arm may not preserve a 6D
tool orientation while tracing every segment. Never assume LIN succeeds.
"""
import argparse
import copy
from pathlib import Path
import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped
from moveit.planning import MoveItPy
from moveit_configs_utils import MoveItConfigsBuilder


def square_offsets(size):
    """40cm and 10cm terminology is made explicit: size is in METRES."""
    if not 0 < size <= 0.4:
        raise ValueError("size must be in (0, 0.4] metres")
    # X-Z plane; each move is relative to the previous corner.
    return [(0.0, 0.0, -size), (size, 0.0, 0.0),
            (0.0, 0.0, size), (-size, 0.0, 0.0)]


def build_config():
    description = Path(get_package_share_directory("my_robot_description"))
    urdf = description / "urdf" / "my_robot.urdf.xacro"
    if not urdf.exists():
        raise FileNotFoundError(urdf)
    builder = (
        MoveItConfigsBuilder("my_robot", package_name="my_robot_moveit_config")
        .robot_description(file_path=str(urdf))
        .robot_description_semantic(file_path="config/my_robot.srdf")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .joint_limits(file_path="config/joint_limits.yaml")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(
            pipelines=["pilz_industrial_motion_planner"],
            default_planning_pipeline="pilz_industrial_motion_planner",
        )
        .to_moveit_configs()
    )
    params = builder.to_dict()
    pipeline_data = params.get("planning_pipelines", {})
    pilz = (pipeline_data.get("pilz_industrial_motion_planner")
            if isinstance(pipeline_data, dict) else None)
    if not pilz or not pilz.get("planning_plugins"):
        raise RuntimeError("Pilz CommandPlanner config not loaded")
    params["pilz_industrial_motion_planner"] = pilz
    params["planning_pipelines"] = {
        "pipeline_names": ["pilz_industrial_motion_planner"],
        "default_planning_pipeline": "pilz_industrial_motion_planner",
    }
    params["planning_scene_monitor_options"] = {
        "name": "planning_scene_monitor", "robot_description": "robot_description",
        "joint_state_topic": "/joint_states", "wait_for_initial_state_timeout": 10.0,
    }
    params["plan_request_params"] = {
        "planning_pipeline": "pilz_industrial_motion_planner",
        "planner_id": "LIN", "planning_attempts": 1, "planning_time": 5.0,
        "max_velocity_scaling_factor": 0.1,
        "max_acceleration_scaling_factor": 0.1,
    }
    return params


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=float, default=0.1, help="side length in metres")
    parser.add_argument("--execute", action="store_true",
                        help="ONLY in verified mock/Gazebo; sequential four segments")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    try:
        offsets = square_offsets(args.size)
    except ValueError as exc:
        print(exc)
        return 2
    rclpy.init()
    try:
        robot = MoveItPy(node_name="ch06_cartesian_lin", config_dict=build_config())
        arm = robot.get_planning_component("arm_group")
        with robot.get_planning_scene_monitor().read_only() as scene:
            current = copy.deepcopy(scene.current_state.get_pose("link_wrist"))
        target = PoseStamped()
        target.header.frame_id = "base_link"
        target.pose = current

        if not args.execute:
            print("PLAN ONLY: first LIN segment preview; no square execution")
        for i, (dx, dy, dz) in enumerate(offsets if args.execute else offsets[:1], 1):
            target.pose.position.x += dx
            target.pose.position.y += dy
            target.pose.position.z += dz
            arm.set_start_state_to_current_state()
            arm.set_goal_state(pose_stamped_msg=target, pose_link="link_wrist")
            plan = arm.plan()
            if not plan:
                print(f"FAIL: LIN segment {i}; IK/collision/limits need investigation")
                return 1
            print(f"PASS: LIN segment {i} PLANNED, not yet physically verified")
            if args.execute:
                status = robot.execute(plan.trajectory, controllers=[])
                print(f"SEGMENT {i} EXECUTION RESULT: {status!s}")
                if "SUCCEEDED" not in str(status).upper():
                    print("STOP: execution not confirmed by controller")
                    return 3
                # The next segment uses the latest state; do not replace it with
                # the target merely because a plan existed.
        print("Cartesian path validation still requires sampled FK straightness, "
              "collision clearance and joint velocity limits.")
        return 0
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"SETUP FAIL: {exc}")
        return 4
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
