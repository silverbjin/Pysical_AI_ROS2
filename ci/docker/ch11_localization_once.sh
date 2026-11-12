#!/usr/bin/env bash
# Same pinned GHCR base; explicit transient apt overlay only for missing Jazzy EKF/SLAM binaries.
# No Docker image rebuild or change to textbook content.
set -Eeuo pipefail
OUT=/work/ci-results/next/Ch11
mkdir -p "$OUT"
echo "ENVIRONMENT_ADDONS_START" | tee "$OUT/addons_stage.txt"
if ! test -x /opt/ros/jazzy/lib/robot_localization/ekf_node || \
   ! test -x /opt/ros/jazzy/lib/slam_toolbox/async_slam_toolbox_node; then
  echo "INSTALL_EPHEMERAL_APT_ROS_JAZZY_ROBOT_LOCALIZATION_SLAM_TOOLBOX" | tee -a "$OUT/addons_stage.txt"
  export DEBIAN_FRONTEND=noninteractive
  timeout --signal=TERM --kill-after=8s 105s apt-get update -qq > "$OUT/apt_update.log" 2>&1
  timeout --signal=TERM --kill-after=8s 105s \
    apt-get install -y --no-install-recommends \
      ros-jazzy-robot-localization ros-jazzy-slam-toolbox \
    > "$OUT/apt_install.log" 2>&1
fi
dpkg-query -W ros-jazzy-robot-localization ros-jazzy-slam-toolbox \
  > "$OUT/addon_versions.txt"
echo "ENVIRONMENT_ADDONS_READY" | tee -a "$OUT/addons_stage.txt"
exec bash /work/ci/docker/next_scope.sh Ch11
