#!/usr/bin/env bash
# Ch03–Ch05 bounded probes executed from the SAME prebuilt Docker image.
set -Eeuo pipefail
set +u
source /opt/ros/jazzy/setup.bash
set -u
CHAPTER="$1"
case "$CHAPTER" in Ch03|Ch04|Ch05) ;; *) echo "Usage: smoke.sh Ch03|Ch04|Ch05" >&2; exit 2 ;; esac
ROOT=/work
OUT="$ROOT/ci-results/gazebo/$CHAPTER"
mkdir -p "$OUT"
echo "source_sha=$GITHUB_SHA" > "$OUT/env.txt"
echo "ros_distro=$ROS_DISTRO" >> "$OUT/env.txt"
ros2 pkg prefix ros_gz_sim | tee -a "$OUT/env.txt"
ros2 pkg prefix gz_ros2_control | tee -a "$OUT/env.txt"
echo 'STAGE=GZ_HELP' | tee -a "$OUT/stages.log"
timeout 20s gz sim --help > "$OUT/gz_help.txt"
grep -Eq 'Gazebo|gazebo|sim' "$OUT/gz_help.txt"

export ROS_DOMAIN_ID=73
export GZ_PARTITION="book_$CHAPTER-$$_$RANDOM"
export GZ_IP=127.0.0.1
export QT_QPA_PLATFORM=offscreen
export LIBGL_ALWAYS_SOFTWARE=1

PKG=""
case "$CHAPTER" in
  Ch03) PKG="my_robot_description" ;;
  Ch04) PKG="my_robot_tf" ;;
  Ch05) PKG="manipulation_basics" ;;
esac
WS="$ROOT/$CHAPTER/ros2_ws"
echo 'STAGE=BUILD' | tee -a "$OUT/stages.log"
cd "$WS"
python3 -m compileall -q src
timeout --signal=TERM --kill-after=10s 150s \
  colcon build --symlink-install --packages-select "$PKG" \
  2>&1 | tee "$OUT/colcon.log"
set +u
source install/setup.bash
set -u
ros2 pkg prefix "$PKG" | tee "$OUT/prefix.txt"

echo 'STAGE=CHAPTER_SPECIFIC' | tee -a "$OUT/stages.log"
if [[ "$CHAPTER" == Ch04 ]]; then
  ros2 run my_robot_tf static_tf_broadcaster > "$OUT/static_tf.log" 2>&1 &
  TF_PID=$!
  trap 'kill -INT "$TF_PID" 2>/dev/null || true; wait "$TF_PID" 2>/dev/null || true' EXIT
  timeout 25s ros2 topic echo /tf_static --once --qos-durability transient_local > "$OUT/tf_echo.txt"
  grep -q "lidar_sensor_link" "$OUT/tf_echo.txt"
  echo 'CH04_TF_STATIC_PASS_GAZEBO_NOT_RUN' | tee "$OUT/verdict.txt"
  exit 0
fi

if [[ "$CHAPTER" == Ch05 ]]; then
  xacro "$WS/src/manipulation_basics/urdf/robot.urdf.xacro" > "$OUT/robot.urdf"
  check_urdf "$OUT/robot.urdf" > "$OUT/urdf_check.txt"
  grep -q "link4" "$OUT/urdf_check.txt"
  echo 'CH05_XACRO_PARSE_PASS_CONTROLLER_RUNTIME_NOT_RUN' | tee "$OUT/verdict.txt"
  exit 0
fi

# The book's actual Ch03 world and model: server-only mode, no GUI.
xacro "$WS/src/my_robot_description/urdf/two_dof_arm.urdf.xacro" > "$OUT/arm.urdf"
check_urdf "$OUT/arm.urdf" > "$OUT/urdf_check.txt"
WORLD="$WS/src/my_robot_description/worlds/my_world.sdf"
gz sim -s -r -v 2 "$WORLD" > "$OUT/gz_server.log" 2>&1 &
GZ_PID=$!
BRIDGE_PID=""
stop_owned() {
  local pid="$1" label="$2"
  [[ -z "$pid" ]] && return 0
  kill -INT "$pid" 2>/dev/null || true
  for i in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid" 2>/dev/null || true
      return 0
    fi
    sleep 0.1
  done
  echo "SHUTDOWN_ESCALATED_TERM:$label" | tee -a "$OUT/stages.log"
  kill -TERM "$pid" 2>/dev/null || true
  for i in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid" 2>/dev/null || true
      return 0
    fi
    sleep 0.1
  done
  echo "SHUTDOWN_ESCALATED_KILL:$label" | tee -a "$OUT/stages.log"
  kill -KILL "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}
cleanup() {
  set +e
  stop_owned "$BRIDGE_PID" bridge
  stop_owned "$GZ_PID" gz
}
trap cleanup EXIT

READY=0
echo 'STAGE=WAIT_GZ_WORLD' | tee -a "$OUT/stages.log"
for i in $(seq 1 15); do
  if timeout 3s gz service -l 2>/dev/null | grep -q '/world/my_first_world/create'; then READY=1; break; fi
  if ! kill -0 "$GZ_PID" 2>/dev/null; then break; fi
  sleep 1
done
if [[ "$READY" != 1 ]]; then
  echo 'CH03_WORLD_SERVICE_NOT_READY' | tee "$OUT/verdict.txt"
  tail -100 "$OUT/gz_server.log"
  exit 1
fi
echo 'STAGE=CREATE_ENTITY' | tee -a "$OUT/stages.log"
timeout 45s ros2 run ros_gz_sim create -world my_first_world \
  -name my_arm_test -file "$OUT/arm.urdf" -z 0.1 \
  2>&1 | tee "$OUT/spawn.log"
grep -Ei 'success|created' "$OUT/spawn.log" >/dev/null || { echo 'Spawn success not observed'; exit 1; }

ros2 run ros_gz_bridge parameter_bridge \
  '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock' > "$OUT/bridge.log" 2>&1 &
BRIDGE_PID=$!
echo 'STAGE=BRIDGE_CLOCK' | tee -a "$OUT/stages.log"
timeout 35s ros2 topic echo /clock --once > "$OUT/clock.txt"
grep -q 'sec:' "$OUT/clock.txt"
echo 'CH03_GAZEBO_HEADLESS_WORLD_SPAWN_CLOCK_PASS_GUI_NOT_RUN' | tee "$OUT/verdict.txt"
