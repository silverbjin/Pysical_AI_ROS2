#!/usr/bin/env python3
"""Ch06 §6.5: measured, four-segment Pilz LIN Cartesian rectangle.

SIMULATION ONLY. Exact installed Ch06 robot model, a single FK-derived
reachable starting pose, and the existing fake ros2_control launch are used.
Each LIN trajectory is checked for straightness BEFORE it is executed; actual
/joint_states history then checks executed straightness separately.
This is not Gazebo physics, RViz, or physical robot safety validation.
"""
import argparse
import copy
import json
import math
import os
from pathlib import Path
import sys
import threading
import time

from geometry_msgs.msg import PoseStamped
from moveit.planning import MoveItPy, PlanRequestParameters
from moveit_configs_utils import MoveItConfigsBuilder
from rclpy.node import Node
from sensor_msgs.msg import JointState
import rclpy

from my_robot_control.hello_moveit import ARM_JOINTS, robot_model_path
from my_robot_control.pose_ik_fk import pose_from_joints, pose_error

TIP = "link_wrist"
FRAME = "world"
ARM = "arm_group"
# Small, physically reachable X-Z test. This is intentionally NOT the
# old unverified 0.40m rectangle, and not the draft's 0.10m Y-Z claim.
SIDE_M = 0.04
MOVES = ((0., 0., -SIDE_M), (SIDE_M, 0., 0.),
         (0., 0., SIDE_M), (-SIDE_M, 0., 0.))
FK_SEED = {
    "joint1": 0.0, "joint2": -0.25, "joint3": 0.95,
    "joint4": 0.0, "joint_wrist": -0.70,
}
POSITION_TOL_M = 0.03
ORIENTATION_TOL_RAD = 0.10
PLANNED_LINE_TOL_M = 0.012
OBSERVED_LINE_TOL_M = 0.025


def build_cartesian_config():
    cfg = (MoveItConfigsBuilder("my_robot", package_name="my_robot_moveit_config")
           .robot_description(file_path=robot_model_path())
           .robot_description_semantic(file_path="config/my_robot.srdf")
           .robot_description_kinematics(file_path="config/kinematics.yaml")
           .joint_limits(file_path="config/joint_limits.yaml")
           .trajectory_execution(file_path="config/moveit_controllers.yaml")
           .planning_pipelines(pipelines=["pilz_industrial_motion_planner"])
           .pilz_cartesian_limits()
           .to_moveit_configs().to_dict())
    plugin = cfg.get("pilz_industrial_motion_planner", {}).get("planning_plugins", [])
    assert "pilz_industrial_motion_planner/CommandPlanner" in plugin, (
        "CH06_65_PILZ_COMMAND_PLANNER_NOT_CONFIGURED"
    )
    limits = cfg.get("robot_description_planning", {}).get("cartesian_limits", {})
    assert all(float(limits.get(k, 0.)) > 0. for k in
               ("max_trans_vel", "max_trans_acc", "max_rot_vel")), (
        "CH06_65_PILZ_CARTESIAN_LIMITS_MISSING"
    )
    assert float(limits.get("max_trans_dec", 0.)) < 0., (
        "CH06_65_PILZ_DECELERATION_LIMIT_MISSING"
    )
    # Same explicit nested MoveItCpp/Jazzy configuration style as accepted
    # #133/#135, but selecting the real Pilz CommandPlanner, never OMPL.
    cfg["planning_pipelines"] = {
        "pipeline_names": ["pilz_industrial_motion_planner"],
        "default_planning_pipeline": "pilz_industrial_motion_planner",
    }
    cfg["plan_request_params"] = {
        "planning_pipeline": "pilz_industrial_motion_planner",
        "planner_id": "PTP", "planning_attempts": 1,
        "planning_time": 5.0,
        "max_velocity_scaling_factor": 0.1,
        "max_acceleration_scaling_factor": 0.1,
    }
    cfg["planning_scene_monitor_options"] = {
        "name": "planning_scene_monitor",
        "robot_description": "robot_description",
        "joint_state_topic": "/joint_states",
        "wait_for_initial_state_timeout": 10.0,
    }
    return cfg


class JointHistory(Node):
    """Fresh measured states recorded throughout synchronous MoveIt execute()."""
    def __init__(self):
        super().__init__("ch06_65_joint_history")
        self.lock = threading.Lock()
        self.history = []
        self.message_count = 0
        self.last_stamp_ns = 0
        self.create_subscription(JointState, "/joint_states", self._receive, 10)

    def _receive(self, msg):
        values = dict(zip(msg.name, msg.position))
        if not all(j in values and math.isfinite(values[j]) for j in ARM_JOINTS):
            return
        stamp = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
        with self.lock:
            self.message_count += 1
            self.history.append((self.message_count,
                                 {j: float(values[j]) for j in ARM_JOINTS},
                                 stamp))
            self.last_stamp_ns = stamp

    def snapshot(self):
        with self.lock:
            return list(self.history)

    def wait_for(self, predicate, timeout=15.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            history = self.snapshot()
            if history and predicate(history[-1][1], history[-1][0]):
                return history[-1]
            time.sleep(0.05)
        raise TimeoutError("CH06_65_FRESH_JOINT_FEEDBACK_MISSING")


def distance_to_segment(point, start, end):
    a = (start.position.x, start.position.y, start.position.z)
    b = (end.position.x, end.position.y, end.position.z)
    p = (point.position.x, point.position.y, point.position.z)
    v = tuple(bi - ai for ai, bi in zip(a, b))
    w = tuple(pi - ai for ai, pi in zip(a, p))
    denom = sum(x * x for x in v)
    if denom < 1e-6:
        raise RuntimeError("CH06_65_ZERO_LENGTH_SEGMENT")
    t = min(1.0, max(0.0, sum(x * y for x, y in zip(w, v)) / denom))
    return math.sqrt(sum((pi - ai - t * vi) ** 2
                         for pi, ai, vi in zip(p, a, v)))


def params(robot, planner_id):
    # Jazzy binding requires explicit namespace argument, even for defaults.
    req = PlanRequestParameters(robot, "")
    req.planning_pipeline = "pilz_industrial_motion_planner"
    req.planner_id = planner_id
    req.planning_attempts = 1
    req.planning_time = 5.0
    req.max_velocity_scaling_factor = 0.1
    req.max_acceleration_scaling_factor = 0.1
    return req


def planned_line_evidence(model, trajectory, start_pose, target_pose):
    msg = trajectory.get_robot_trajectory_msg().joint_trajectory
    names = list(msg.joint_names)
    if not all(j in names for j in ARM_JOINTS):
        raise RuntimeError("CH06_65_PLANNED_TRAJECTORY_JOINT_NAMES_MISSING")
    points = list(msg.points)
    if len(points) < 3:
        raise RuntimeError(f"CH06_65_TOO_FEW_PLANNED_POINTS count={len(points)}")
    distances = []
    for p in points:
        joint_map = dict(zip(names, p.positions))
        pose = pose_from_joints(model, {j: joint_map[j] for j in ARM_JOINTS})
        distances.append(distance_to_segment(pose, start_pose, target_pose))
    return max(distances), len(points)


def make_pose(start, delta):
    target = PoseStamped()
    target.header.frame_id = FRAME
    target.pose = copy.deepcopy(start)
    target.pose.position.x += delta[0]
    target.pose.position.y += delta[1]
    target.pose.position.z += delta[2]
    return target


def run_cartesian(robot, recorder):
    # Wait for a fresh real stream after MoveItCpp initializes its own monitor.
    first = recorder.wait_for(lambda _j, _n: True)
    count = first[0]
    time.sleep(3.0)
    recent = recorder.snapshot()
    now = recorder.get_clock().now().nanoseconds
    age_sec = (now - recent[-1][2]) / 1e9
    if recent[-1][0] - count < 20 or not (-0.5 <= age_sec <= 1.0):
        raise RuntimeError("CH06_65_STALE_JOINT_STATE_AFTER_MOVEIT_INIT")
    print(f"CH06_65_FRESH_JOINT_STREAM_PASS samples={recent[-1][0]-count}",
          flush=True)

    model = robot.get_robot_model()
    planning = robot.get_planning_component(ARM)
    start_seed_pose = pose_from_joints(model, FK_SEED)
    seed = PoseStamped()
    seed.header.frame_id = FRAME
    seed.pose = start_seed_pose
    planning.set_start_state_to_current_state()
    if not planning.set_goal_state(pose_stamped_msg=seed, pose_link=TIP):
        raise RuntimeError("CH06_65_PREPOSITION_PTP_IK_GOAL_REJECTED")
    ptp = planning.plan(single_plan_parameters=params(robot, "PTP"))
    if not ptp:
        raise RuntimeError("CH06_65_PREPOSITION_PTP_PLANNING_FAIL")
    print("CH06_65_PILZ_PTP_PREPOSITION_PLANNING_PASS", flush=True)
    pre = robot.execute(ptp.trajectory, controllers=[])
    if not bool(pre) or str(pre.status).upper() != "SUCCEEDED":
        raise RuntimeError(f"CH06_65_PTP_EXECUTION_FAIL status={pre.status}")
    previous_count = recorder.snapshot()[-1][0]
    _, current, _ = recorder.wait_for(
        lambda j, n: (n > previous_count and
                      pose_error(pose_from_joints(model, j),
                                 start_seed_pose)[0] <= POSITION_TOL_M and
                      pose_error(pose_from_joints(model, j),
                                 start_seed_pose)[1] <= ORIENTATION_TOL_RAD),
        timeout=12.0,
    )
    baseline = pose_from_joints(model, current)
    print("CH06_65_PTP_POSITIONING_EXECUTION_AND_FK_PASS", flush=True)

    segment_receipts = []
    start = baseline
    for i, delta in enumerate(MOVES, start=1):
        target = make_pose(start, delta)
        target.header.stamp = recorder.get_clock().now().to_msg()
        planning.set_start_state_to_current_state()
        if not planning.set_goal_state(pose_stamped_msg=target, pose_link=TIP):
            raise RuntimeError(f"CH06_65_LIN_GOAL_REJECTED segment={i}")
        result = planning.plan(single_plan_parameters=params(robot, "LIN"))
        if not result:
            raise RuntimeError(f"CH06_65_PILZ_LIN_PLANNING_FAIL segment={i}")
        planned_line, point_count = planned_line_evidence(
            model, result.trajectory, start, target.pose)
        if planned_line > PLANNED_LINE_TOL_M:
            raise RuntimeError(
                f"CH06_65_PLANNED_NOT_LINEAR segment={i} error={planned_line:.6f}"
            )
        print(
            f"CH06_65_LIN_PLANNED_PATH_PASS segment={i} "
            f"max_deviation_m={planned_line:.6f} points={point_count}",
            flush=True,
        )

        counter = recorder.snapshot()[-1][0]
        exec_result = robot.execute(result.trajectory, controllers=[])
        if not bool(exec_result) or str(exec_result.status).upper() != "SUCCEEDED":
            raise RuntimeError(
                f"CH06_65_LIN_EXECUTION_FAIL segment={i} status={exec_result.status}"
            )
        _, observed, _ = recorder.wait_for(
            lambda j, n: (n > counter and
                          pose_error(pose_from_joints(model, j),
                                     target.pose)[0] <= POSITION_TOL_M and
                          pose_error(pose_from_joints(model, j),
                                     target.pose)[1] <= ORIENTATION_TOL_RAD),
            timeout=12.0,
        )
        actual_end = pose_from_joints(model, observed)
        ep, ea = pose_error(actual_end, target.pose)
        actual_points = [j for n, j, _s in recorder.snapshot() if n > counter]
        if len(actual_points) < 5:
            raise RuntimeError(f"CH06_65_MEASURED_PATH_TOO_SPARSE segment={i}")
        observed_line = max(distance_to_segment(
            pose_from_joints(model, j), start, target.pose) for j in actual_points)
        if observed_line > OBSERVED_LINE_TOL_M:
            raise RuntimeError(
                f"CH06_65_MEASURED_NOT_LINEAR segment={i} deviation={observed_line:.6f}"
            )
        print(
            f"CH06_65_LIN_EXECUTION_AND_MEASURED_PATH_PASS segment={i} "
            f"position_error_m={ep:.6f} orientation_error_rad={ea:.6f} "
            f"observed_max_line_deviation_m={observed_line:.6f} "
            f"observed_samples={len(actual_points)}",
            flush=True,
        )
        segment_receipts.append({
            "segment": i, "move_xyz_m": list(delta),
            "planner": "pilz_industrial_motion_planner/LIN",
            "planned_points": point_count,
            "planned_max_deviation_m": planned_line,
            "measured_samples": len(actual_points),
            "measured_max_deviation_m": observed_line,
            "position_error_m": ep,
            "orientation_error_rad": ea,
            "execution": str(exec_result.status),
        })
        start = actual_end

    closed_p, closed_a = pose_error(start, baseline)
    if closed_p > POSITION_TOL_M or closed_a > ORIENTATION_TOL_RAD:
        raise RuntimeError(
            f"CH06_65_PATH_NOT_CLOSED pos={closed_p:.6f} angle={closed_a:.6f}"
        )
    print(f"CH06_65_FOUR_SEGMENT_CLOSED_PATH_PASS closure_m={closed_p:.6f}",
          flush=True)
    return {
        "chapter": "Ch06", "section": "6.5",
        "scenario": "four_segment_pilz_lin_xz_mock_controller",
        "side_length_m": SIDE_M, "frame": FRAME, "tip": TIP,
        "pilz_ptp_preposition": "PASS",
        "pilz_lin_segments": segment_receipts,
        "closure_position_error_m": closed_p,
        "closure_orientation_error_rad": closed_a,
        "position_tolerance_m": POSITION_TOL_M,
        "orientation_tolerance_rad": ORIENTATION_TOL_RAD,
        "planned_line_tolerance_m": PLANNED_LINE_TOL_M,
        "measured_line_tolerance_m": OBSERVED_LINE_TOL_M,
        "normal_moveitcpp_destructor": "NOT_RUN_UPSTREAM_MOVEIT2_3721",
        "gazebo_physics": "NOT_RUN", "rviz_gui": "NOT_RUN",
        "hardware": "NOT_RUN", "ch10": "HOLD",
        "other_chapter_retests": "NOT_RUN",
    }


def main(args=None):
    parser = argparse.ArgumentParser(description="Real Pilz LIN 4-segment Cartesian validation.")
    parser.add_argument("--ci-mock-verified-exit", action="store_true")
    known, ros_args = parser.parse_known_args(args)
    if not (known.ci_mock_verified_exit
            and os.environ.get("CH06_CI_MOCK_CONTROLLER_VERIFIED") == "1"
            and os.environ.get("CH06_CI_RESULT_RECEIPT")):
        print("CH06_65_MOCK_ONLY_GUARD_REQUIRED", file=sys.stderr, flush=True)
        return 2
    rclpy.init(args=ros_args)
    robot = None
    recorder = JointHistory()
    stop = threading.Event()

    def spin_history():
        while not stop.is_set() and rclpy.ok():
            rclpy.spin_once(recorder, timeout_sec=0.1)

    spin_thread = threading.Thread(target=spin_history, daemon=True)
    spin_thread.start()
    try:
        config = build_cartesian_config()
        print("CH06_65_PILZ_CONFIG_AND_CARTESIAN_LIMITS_PASS", flush=True)
        recorder.wait_for(lambda _j, _n: True, timeout=15.0)
        robot = MoveItPy(node_name="ch06_65_cartesian_lin", config_dict=config)
        data = run_cartesian(robot, recorder)
        receipt = Path(os.environ["CH06_CI_RESULT_RECEIPT"])
        receipt.parent.mkdir(parents=True, exist_ok=True)
        temp = receipt.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, receipt)
        print("CH06_65_PILZ_LIN_FULL_SCOPED_PASS_MOCK_ONLY", flush=True)
        print("CH06_65_UPSTREAM_3721_TEARDOWN_BYPASSED_AFTER_VERIFIED_EXECUTION",
              flush=True)
        stop.set()
        spin_thread.join(timeout=1.0)
        recorder.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        sys.stdout.flush()
        sys.stderr.flush()
        # The same mock-only post-evidence workaround as accepted Ch06 #133.
        # Normal MoveItPy Jazzy destructor remains NOT_RUN, never used on hardware.
        os.execv("/usr/bin/true", ["true"])
        raise AssertionError("execv unexpectedly returned")
    except (Exception, KeyboardInterrupt) as exc:
        print(f"CH06_65_FAIL type={type(exc).__name__} reason={exc}",
              file=sys.stderr, flush=True)
        return 1
    finally:
        stop.set()
        spin_thread.join(timeout=1.0)
        if robot is not None:
            del robot
        if rclpy.ok():
            recorder.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
