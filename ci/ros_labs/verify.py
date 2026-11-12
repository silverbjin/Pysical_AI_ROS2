#!/usr/bin/env python3
"""Headless ROS 2 textbook integration probes. Evidence is scoped to the checks executed.

Does not claim GUI observation, manual fault-injection, or every command in a LAB
has been reproduced. Each section's first failing command remains in its log.
"""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
CHAPTER = sys.argv[1] if len(sys.argv) > 1 else ""
if CHAPTER not in ("Ch01", "Ch02"):
    sys.exit("Usage: python3 ci/ros_labs/verify.py Ch01|Ch02")
OUT = ROOT / "ci-results" / CHAPTER / "ros-sections"
OUT.mkdir(parents=True, exist_ok=True)
os.environ["ROS_DOMAIN_ID"] = "61" if CHAPTER == "Ch01" else "62"
os.environ["ROS_LOCALHOST_ONLY"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["DISPLAY"] = ":98"
PROCS = []
FILES = []
REPORT = {}
CURRENT = None


def trace(message):
    line = str(message)
    print(line, flush=True)
    with (OUT / "commands.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(args, timeout=25, expected=0, cwd=None):
    trace("RUN " + " ".join(map(str, args)))
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=timeout, env=os.environ.copy(), cwd=cwd)
    except subprocess.TimeoutExpired as exc:
        trace("TIMEOUT after " + str(timeout) + "s")
        raise AssertionError("Command timed out: " + str(args)) from exc
    trace(p.stdout[-3000:])
    if expected is not None and p.returncode != expected:
        raise AssertionError("Command exit " + str(p.returncode) + ": " + str(args))
    return p.stdout


def start(tag, args):
    path = OUT / (CURRENT + "_" + tag + ".log")
    handle = path.open("w", encoding="utf-8")
    process = subprocess.Popen(args, stdout=handle, stderr=subprocess.STDOUT,
                               env=os.environ.copy(), start_new_session=True)
    PROCS.append(process)
    FILES.append(handle)
    trace("START " + tag + " pid=" + str(process.pid) + " " + " ".join(args))
    return process, path


def finish():
    for process in reversed(PROCS):
        if process.poll() is not None:
            continue
        try:
            os.killpg(process.pid, signal.SIGINT)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            trace("SHUTDOWN_TERM pid=" + str(process.pid))
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=3)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                trace("SHUTDOWN_KILL pid=" + str(process.pid))
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
    for handle in FILES:
        handle.close()
    PROCS.clear()
    FILES.clear()


def until(func, seconds=15, label="readiness"):
    end = time.monotonic() + seconds
    last = None
    while time.monotonic() < end:
        try:
            result = func()
            if result:
                return result
        except Exception as exc:
            last = str(exc)
        time.sleep(0.4)
    raise AssertionError(label + " not ready; last=" + str(last))


def grep(path, regex, seconds=8):
    return until(lambda: bool(re.search(regex, path.read_text(errors="replace"))),
                 seconds, "log " + path.name + ": " + regex)


def node(name):
    return until(lambda: name in run(["ros2", "node", "list"], timeout=6).split(),
                 16, "node " + name)


def topic_once(topic, msg_type=None):
    args = ["ros2", "topic", "echo", topic]
    if msg_type:
        args.append(msg_type)
    args.append("--once")
    return run(args, timeout=20)


def check(name, func):
    trace("CHECK " + name)
    value = func()
    REPORT[CURRENT]["checks"].append({"name": name, "status": "PASS"})
    return value


def eq_contains(s, text):
    if text not in s:
        raise AssertionError("Missing " + repr(text) + " in " + repr(s[-900:]))


def required(condition, msg):
    if not condition:
        raise AssertionError(msg)


def case(section, omitted, fn):
    global CURRENT
    CURRENT = section.replace(".", "_")
    REPORT[CURRENT] = {"chapter": CHAPTER, "section": section,
                       "guide": CHAPTER + "/docs/LAB_" + CURRENT + "_GUIDE_KO.md",
                       "status": "RUNNING", "checks": [], "not_automated": omitted}
    try:
        fn()
        REPORT[CURRENT]["status"] = "PARTIAL_PASS" if omitted else "PASS"
    except Exception as exc:
        REPORT[CURRENT]["status"] = "FAIL"
        REPORT[CURRENT]["first_error"] = str(exc)
        trace("FAIL " + section + ": " + str(exc))
        trace(traceback.format_exc()[-2000:])
    finally:
        finish()
        (OUT / "results.json").write_text(json.dumps(REPORT, indent=2, ensure_ascii=False) + "\n")


def setup_x():
    global CURRENT
    CURRENT = "Xvfb"
    start("display", ["Xvfb", ":98", "-screen", "0", "1024x768x24", "-nolisten", "tcp"])
    time.sleep(1)
    required(PROCS[-1].poll() is None, "Xvfb exited")
    # Xvfb is kept running until end of chapter.
    PROCS.clear()
    FILES[-1].close()
    FILES.clear()


def source_workspace(chapter):
    base = ROOT / chapter
    if chapter == "Ch01":
        ws = OUT / "ch01_ws"
        src = ws / "src"
        src.mkdir(parents=True, exist_ok=True)
        origins = [
            base / "robot_ws/src/my_robot_controller",
            base / "robot_ws/src/examples/rclpy/topics/minimal_publisher",
        ]
        for origin in origins:
            required(origin.is_dir(), "Source missing " + str(origin))
            target = src / origin.name
            if not target.exists():
                target.symlink_to(origin, target_is_directory=True)
    else:
        ws = base / "ros2_ws"
    trace("WORKSPACE " + str(ws))
    run(["colcon", "build", "--symlink-install", "--base-paths", str(ws / "src"),
         "--build-base", str(ws / "build"), "--install-base", str(ws / "install"),
         ], timeout=180)
    setup = ws / "install" / "setup.bash"
    envcmd = ["bash", "-c", "source " + str(setup) + " && env -0"]
    p = subprocess.run(envcmd, stdout=subprocess.PIPE, check=True, env=os.environ.copy())
    os.environ.update(dict(item.decode().split("=", 1) for item in p.stdout.split(b"\0") if item and b"=" in item))
    trace("BUILT workspace " + str(ws))
    return ws


def ch01_11():
    _, talk = start("talker", ["ros2", "run", "demo_nodes_cpp", "talker"])
    node("/talker")
    _, listen = start("listener", ["ros2", "run", "demo_nodes_py", "listener"])
    check("talker/listener >= 3", lambda: grep(listen, r"I heard:.*?\d+", 7) and
          until(lambda: len(re.findall("I heard:", listen.read_text(errors="replace"))) >= 3, 8))
    check("chatter String", lambda: eq_contains(run(["ros2", "topic", "type", "/chatter"]), "std_msgs/msg/String"))
    check("QoS endpoints", lambda: eq_contains(run(["ros2", "topic", "info", "-v", "/chatter"]), "Reliability"))


def ch01_12():
    check("Ubuntu noble", lambda: eq_contains(Path("/etc/os-release").read_text(), "VERSION_ID=\"24.04\""))
    check("ROS Jazzy", lambda: required(os.environ.get("ROS_DISTRO") == "jazzy", "Wrong ROS_DISTRO"))
    check("python and rclpy", lambda: run(["python3", "-c", "import rclpy,sys;assert sys.version_info[:2]==(3,12)"]))
    check("ROS CLI / colcon", lambda: (shutil.which("ros2") or required(False, "ros2 missing"),
                                       shutil.which("colcon") or required(False, "colcon missing")))


def turtlesim():
    _, log = start("turtlesim", ["ros2", "run", "turtlesim", "turtlesim_node"])
    node("/turtlesim")
    return log


def ch01_13():
    turtlesim()
    check("Pose topic", lambda: eq_contains(topic_once("/turtle1/pose"), "x:"))
    check("Spawn service", lambda: eq_contains(run(["ros2", "service", "call", "/spawn", "turtlesim/srv/Spawn",
                  "{x: 5.0, y: 5.0, theta: 0.0, name: lab_turtle}"], timeout=20), "lab_turtle"))
    check("RotateAbsolute action", lambda: eq_contains(run(["ros2", "action", "send_goal",
                  "/turtle1/rotate_absolute", "turtlesim/action/RotateAbsolute",
                  "{theta: 1.57}", "--feedback"], timeout=35), "SUCCEEDED"))


def ch01_14():
    check("examples_rclpy package index", lambda: eq_contains(
          run(["ros2", "pkg", "executables", "examples_rclpy_minimal_publisher"]), "publisher_member_function"))
    _, log = start("minimal_publisher", ["ros2", "run", "examples_rclpy_minimal_publisher", "publisher_member_function"])
    check("publisher /topic hello", lambda: eq_contains(topic_once("/topic"), "Hello World"))
    check("source overlay", lambda: required("ch01_ws/install" in os.environ.get("AMENT_PREFIX_PATH", ""),
                                            "Overlay not sourced"))


def ch01_15():
    ws = OUT / "fresh_package"
    src = ws / "src"
    src.mkdir(parents=True, exist_ok=True)
    if not (src / "my_robot_controller").exists():
        check("ros2 pkg create", lambda: run(["ros2", "pkg", "create",
             "--build-type", "ament_python", "--license", "Apache-2.0",
             "--node-name", "simple_controller", "my_robot_controller",
             "--dependencies", "rclpy", "std_msgs"], timeout=30, cwd=src))
    for fname in ("package.xml", "setup.py", "setup.cfg"):
        check("fresh package " + fname, lambda f=fname: required((src / "my_robot_controller" / f).is_file(), f + " missing"))
    check("fresh colcon build", lambda: run(["colcon", "build", "--symlink-install"],
                                           timeout=100, cwd=ws))
    cmd = "source /opt/ros/jazzy/setup.bash && source '" + str(ws / "install/setup.bash") + "' && ros2 run my_robot_controller simple_controller"
    check("generated executable", lambda: run(["bash", "-c", cmd], timeout=20))


def ch01_16():
    check("test_node entry", lambda: eq_contains(run(["ros2", "pkg", "executables", "my_robot_controller"]), "test_node"))
    _, log = start("heartbeat", ["ros2", "run", "my_robot_controller", "test_node"])
    node("/my_robot_node")
    check("Heartbeat 3", lambda: grep(log, "Heartbeat: 3", 8))
    check("no custom heartbeat topic", lambda: required("/heartbeat" not in run(["ros2", "topic", "list"]),
         "Unexpected heartbeat topic"))


def ch01_17():
    check("installed manifest", lambda: required((ROOT/"Ch01/robot_ws/src/my_robot_controller/package.xml").is_file(), "Manifest missing"))
    check("ROS installation entry", lambda: eq_contains(run(["ros2", "pkg", "executables", "my_robot_controller"]), "test_node"))
    check("prefix in isolated workspace", lambda: required("ch01_ws/install" in run(["ros2", "pkg", "prefix", "my_robot_controller"]), "Wrong overlay"))


def ch02_21():
    _, log = start("joint_sensor", ["ros2", "run", "my_robot_system", "joint_sensor"])
    node("/joint_sensor")
    check("sensor timer >= 3 logs", lambda: until(lambda: len(re.findall("Joint Angle:", log.read_text(errors="replace"))) >= 3, 7))
    check("node info", lambda: eq_contains(run(["ros2", "node", "info", "/joint_sensor"]), "/joint_sensor"))


def ch02_22():
    turtlesim()
    check("pose echo", lambda: eq_contains(topic_once("/turtle1/pose"), "x:"))
    check("Twist type", lambda: eq_contains(run(["ros2", "topic", "type", "/turtle1/cmd_vel"]), "geometry_msgs/msg/Twist"))
    check("spawn my_turtle", lambda: eq_contains(run(["ros2", "service", "call", "/spawn", "turtlesim/srv/Spawn",
          "{x: 2.0, y: 2.0, theta: 0.0, name: my_turtle}"]), "my_turtle"))


def ch02_23():
    turtlesim()
    _, pub = start("cmd_pub", ["ros2", "run", "my_robot_system", "turtle_cmd_pub"])
    _, sub = start("pose_sub", ["ros2", "run", "my_robot_system", "turtle_pose_sub"])
    check("Twist command delivered", lambda: eq_contains(topic_once("/turtle1/cmd_vel"), "linear:"))
    check("Pose subscriber active", lambda: grep(sub, r"([Pp]ose|[Xx]:|[Xx]=)", 8))


def ch02_24():
    turtlesim()
    _, serv = start("adder", ["ros2", "run", "my_robot_system", "add_two_ints_server"])
    check("add_two_ints 15", lambda: eq_contains(run(["ros2", "service", "call", "/add_two_ints",
          "example_interfaces/srv/AddTwoInts", "{a: 5, b: 10}"]), "15"))
    check("spawn client", lambda: run(["ros2", "run", "my_robot_system", "turtle_spawn_client"], timeout=20))


def ch02_25():
    check("custom msg", lambda: eq_contains(run(["ros2", "interface", "show", "my_robot_interfaces/msg/HardwareStatus"]), "machine_id"))
    check("custom service", lambda: eq_contains(run(["ros2", "interface", "show", "my_robot_interfaces/srv/ComputeRectangleArea"]), "length"))
    check("custom action", lambda: eq_contains(run(["ros2", "interface", "show", "my_robot_interfaces/action/CountUntil"]), "target_number"))
    check("Python types", lambda: run(["python3", "-c", "from my_robot_interfaces.msg import HardwareStatus; from my_robot_interfaces.srv import ComputeRectangleArea; from my_robot_interfaces.action import CountUntil;assert HardwareStatus(machine_id=101).machine_id==101"]))
    _, log = start("hw_pub", ["ros2", "run", "my_robot_system", "hw_status_publisher"])
    check("hardware topic", lambda: eq_contains(topic_once("/hardware_status"), "machine_id: 101"))


def ch02_26():
    _, log = start("count_server", ["ros2", "run", "my_robot_system", "count_until_server"])
    node("/count_until_server")
    check("count goal result 5", lambda: eq_contains(run(["ros2", "action", "send_goal", "/count_until",
        "my_robot_interfaces/action/CountUntil", "{target_number: 5, period: 0.1}", "--feedback"], timeout=25), "SUCCEEDED"))
    check("rejection 0", lambda: eq_contains(run(["ros2", "action", "send_goal", "/count_until",
        "my_robot_interfaces/action/CountUntil", "{target_number: 0, period: 1.0}"], timeout=25), "rejected"))


def ch02_27():
    _, good = start("normal", ["ros2", "launch", "my_robot_system", "my_turtle.launch.py"])
    for label in ("/sim", "/my_publisher", "/my_subscriber"):
        check("normal launch " + label, lambda n=label: node(n))
    finish()
    _, bad = start("broken_remap", ["ros2", "launch", "my_robot_system", "remap_test.launch.py"])
    check("broken remap publisher", lambda: eq_contains(run(["ros2", "topic", "info", "-v", "/cmd_vel_custom"]), "Publisher count: 1"))
    check("broken remap no subscriber", lambda: eq_contains(run(["ros2", "topic", "info", "-v", "/cmd_vel_custom"]), "Subscription count: 0"))
    finish()
    _, good2 = start("fixed_remap", ["ros2", "launch", "my_robot_system", "remap_fixed.launch.py"])
    check("fixed publisher", lambda: eq_contains(run(["ros2", "topic", "info", "-v", "/cmd_vel_custom"]), "Publisher count: 1"))
    check("fixed subscription", lambda: eq_contains(run(["ros2", "topic", "info", "-v", "/cmd_vel_custom"]), "Subscription count: 1"))


def ch02_28():
    _, source = start("qos_pub", ["ros2", "run", "my_robot_system", "qos_test_node"])
    check("video topic", lambda: eq_contains(run(["ros2", "topic", "echo", "/video_stream", "--once", "--qos-reliability", "best_effort"], timeout=20), "Frame Data"))
    _, bad = start("incompatible", ["ros2", "run", "my_robot_system", "qos_compare_sub",
                                  "--ros-args", "-p", "reliability:=reliable"])
    time.sleep(3)
    check("incompatible no delivery", lambda: required("Received frame" not in bad.read_text(errors="replace"), "Unexpected compatible QoS"))
    finish()
    _, source = start("qos_pub_ok", ["ros2", "run", "my_robot_system", "qos_test_node"])
    _, good = start("compatible", ["ros2", "run", "my_robot_system", "qos_compare_sub",
                                  "--ros-args", "-p", "reliability:=best_effort"])
    check("compatible received >= 2", lambda: until(lambda: good.read_text(errors="replace").count("Received frame") >= 2, 8))


def main():
    global CURRENT
    CURRENT = "SETUP"
    setup_x()
    if CHAPTER == "Ch01":
        source_workspace(CHAPTER)
        cases = [
            ("1.1", ["SROS2/ROS1 security and visual rqt analysis"], ch01_11),
            ("1.2", ["ROS apt installation from scratch, setup of ~/.bashrc"], ch01_12),
            ("1.3", ["GUI visual examination", "topic rate manual report"], ch01_13),
            ("1.4", ["manual overlay source comparison"], ch01_14),
            ("1.5", ["interactive node initial/final difference"], ch01_15),
            ("1.6", ["editing 1.0s timer to 0.5s", "manual OOP explanation"], ch01_16),
            ("1.7", ["editing setup.py and testing data_files"], ch01_17),
        ]
    else:
        source_workspace(CHAPTER)
        cases = [
            ("2.1", ["timer 0.2s source modification"], ch02_21),
            ("2.2", ["keyboard teleop", "GUI observation"], ch02_22),
            ("2.3", ["fault injection by changing topic name", "GUI observation"], ch02_23),
            ("2.4", ["service absence timeout", "duplicate name fault"], ch02_24),
            ("2.5", ["manual instruction analysis"], ch02_25),
            ("2.6", ["Action Cancel final status", "missing-server timeout"], ch02_26),
            ("2.7", ["GUI motion confirmed by observer", "launch event readiness manual"], ch02_27),
            ("2.8", ["GUI and QoS rate estimate"], ch02_28),
        ]
    for section, omissions, fn in cases:
        case(section, omissions, fn)
    failures = [x for x in REPORT.values() if x["status"] == "FAIL"]
    summary = "# " + CHAPTER + " ROS 2 runtime scope\n\n"
    summary += "| Section | CI checks | Guide overall |\n|---|---|---|\n"
    for x in REPORT.values():
        summary += "| " + x["section"] + " | " + x["status"] + " | NOT_FULLY_ACCEPTED |\n"
    summary += "\nUntested guide steps are listed in results.json; GUI is headless via Xvfb.\n"
    (OUT / "SUMMARY.md").write_text(summary)
    print(summary, flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        finish()
