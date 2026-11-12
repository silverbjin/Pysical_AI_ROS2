#!/usr/bin/env python3
"""Ch06 §6.4: observe -> plan -> execute -> verify (ROS 2 Jazzy / MoveItPy).

Default is the SRDF "ready" joint-state demo. A separate pose-IK exercise
can be added only after its reachable goal and orientation are validated.
SIMULATION ONLY: this is not a physical robot safety controller.
"""
import argparse
import math
from pathlib import Path
import sys
import time

from ament_index_python.packages import get_package_share_directory
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from moveit.planning import MoveItPy
from moveit_configs_utils import MoveItConfigsBuilder

ARM_JOINTS = ("joint1", "joint2", "joint3", "joint4", "joint_wrist")
READY = {"joint1": 0., "joint2": 0., "joint3": 1.5708,
         "joint4": 0., "joint_wrist": 0.}
JOINT_TOLERANCE_RAD = 0.06


def robot_model_path():
    """Use exactly the same installed model as Rviz_Demo.launch.py."""
    path = (Path(get_package_share_directory("my_robot_description"))
            / "urdf" / "my_robot.ros2_control_rviz.urdf.xacro")
    if not path.is_file():
        raise FileNotFoundError(f"Ch06 URDF/Xacro is not installed: {path}")
    return str(path)


def build_moveit_config():
    config_package = "my_robot_moveit_config"
    config = (
        MoveItConfigsBuilder("my_robot", package_name=config_package)
        .robot_description(file_path=robot_model_path())
        .robot_description_semantic(file_path="config/my_robot.srdf")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .joint_limits(file_path="config/joint_limits.yaml")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
        .to_dict()
    )
    # MoveItConfigsBuilder returns 'planning_pipelines' as a list for move_group,
    # while the Jazzy MoveItCpp/MoveItPy constructor needs the nested
    # planning_pipelines.pipeline_names parameter. Preserve the builder's
    # actual ompl_planning.yaml contents in config['ompl'].
    assert "ompl" in config and config["ompl"].get("planning_plugins"), (
        "OMPL planning plugin configuration not loaded"
    )
    config["planning_pipelines"] = {
        "pipeline_names": ["ompl"],
        "default_planning_pipeline": "ompl",
    }
    config["plan_request_params"] = {
        "planning_pipeline": "ompl",
        "planner_id": "RRTConnectkConfigDefault",
        "planning_attempts": 1,
        "planning_time": 5.0,
        "max_velocity_scaling_factor": 0.3,
        "max_acceleration_scaling_factor": 0.3,
    }
    return config


class JointStateObserver(Node):
    def __init__(self):
        super().__init__("ch06_moveit_joint_observer")
        self.last = None
        self.messages = 0
        self.last_stamp_ns = None
        self.create_subscription(JointState, "/joint_states", self._receive, 10)

    def _receive(self, msg):
        observed = dict(zip(msg.name, msg.position))
        if all(name in observed and math.isfinite(observed[name])
               for name in ARM_JOINTS):
            self.last = {name: float(observed[name]) for name in ARM_JOINTS}
            self.messages += 1
            self.last_stamp_ns = (
                msg.header.stamp.sec * 1000000000 + msg.header.stamp.nanosec
            )

    def wait_for(self, condition, timeout_sec):
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.25)
            if self.last is not None and condition(self.last):
                return dict(self.last)
        raise TimeoutError(
            "Ch06 joint state not ready / not at goal: "
            f"messages={self.messages}, last={self.last}"
        )


def run_named_ready(robot, observer):
    before = observer.wait_for(lambda values: True, timeout_sec=15.0)
    print(f"CH06_JOINT_STATES_READY before={before}", flush=True)
    # MoveItCpp creates its *own* C++ joint-state monitor after initialization.
    # The Python subscriber being ready before MoveItCpp exists does not
    # establish DDS readiness of the new internal subscriber. Measure a
    # continuous, fresh state stream after construction before first plan.
    observed_start = observer.messages
    warmup_deadline = time.monotonic() + 3.0
    while time.monotonic() < warmup_deadline:
        rclpy.spin_once(observer, timeout_sec=0.25)
    actual_stamp = observer.last_stamp_ns or 0
    age_sec = (observer.get_clock().now().nanoseconds - actual_stamp) / 1e9
    new_samples = observer.messages - observed_start
    print(
        f"CH06_POST_MOVEIT_MONITOR_STREAM samples={new_samples} "
        f"stamp_ns={actual_stamp} age_sec={age_sec:.3f}",
        flush=True,
    )
    if new_samples < 20 or actual_stamp <= 0 or not (-0.5 <= age_sec <= 1.0):
        raise RuntimeError(
            "CH06_JOINT_STATES_STALE_OR_CLOCK_MISMATCH "
            f"samples={new_samples} stamp={actual_stamp} age={age_sec}"
        )
    planning = robot.get_planning_component("arm_group")
    planning.set_start_state_to_current_state()
    planning.set_goal_state(configuration_name="ready")
    result = planning.plan()
    if not result:
        raise RuntimeError("CH06_NAMED_READY_PLANNING_FAIL")
    print("CH06_NAMED_READY_PLANNING_PASS", flush=True)

    # In Jazzy MoveItPy, execute() returns ExecutionStatus with a
    # .status string and __bool__ implemented for SUCCEEDED.
    execution = robot.execute(result.trajectory, controllers=[])
    status = str(execution.status)
    print(f"CH06_MOVEIT_EXECUTION_STATUS={status}", flush=True)
    if not bool(execution) or status.upper() != "SUCCEEDED":
        raise RuntimeError(f"CH06_EXECUTION_FAIL status={status}")

    n_before = observer.messages
    target = lambda positions: all(abs(positions[name] - READY[name])
                                   <= JOINT_TOLERANCE_RAD for name in ARM_JOINTS)
    observed = observer.wait_for(
        lambda positions: observer.messages > n_before and target(positions),
        timeout_sec=12.0,
    )
    errors = {name: round(abs(observed[name] - READY[name]), 6)
              for name in ARM_JOINTS}
    print(f"CH06_NAMED_READY_EXECUTION_AND_JOINT_GOAL_PASS "
          f"max_error_rad={max(errors.values())} errors={errors}", flush=True)
    return errors


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Ch06 MoveItPy named ready demo; requires headless or RViz demo launch."
    )
    parser.add_argument(
        "--mode", choices=("named",), default="named",
        help="Only measured named ready is accepted; pose-IK is a separate unverified exercise.",
    )
    known, ros_args = parser.parse_known_args(args)
    robot = None
    observer = None
    rclpy.init(args=ros_args)
    try:
        config = build_moveit_config()
        assert "robot_description" in config
        assert "robot_description_semantic" in config
        print("CH06_MODEL_CONFIG_PASS "
              f"model={robot_model_path()} pipelines={config.get('planning_pipelines')}",
              flush=True)
        observer = JointStateObserver()
        # No magic sleeps: readiness is measured from the real controller.
        observer.wait_for(lambda _: True, timeout_sec=15.0)
        robot = MoveItPy(node_name="ch06_hello_moveit", config_dict=config)
        if known.mode == "named":
            run_named_ready(robot, observer)
        print("CH06_64_NAMED_READY_COMPLETE_POSE_IK_NOT_RUN", flush=True)
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        print(f"CH06_64_FAIL type={type(exc).__name__} reason={exc}",
              file=sys.stderr, flush=True)
        return 1
    finally:
        # Never os._exit(0): preserve real error code and release ROS objects.
        if robot is not None:
            del robot
        if observer is not None:
            observer.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
