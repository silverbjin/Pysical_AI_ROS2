#!/usr/bin/env bash
# Same pinned GHCR base; explicit transient apt overlay only for missing Jazzy EKF/SLAM binaries.
# No Docker image rebuild or change to textbook content.
set -Eeuo pipefail
OUT=/work/ci-results/next/Ch11
mkdir -p "$OUT"
echo "ENVIRONMENT_ADDONS_START" | tee "$OUT/addons_stage.txt"
ADDONS=(ros-jazzy-robot-localization ros-jazzy-slam-toolbox)
if [[ "${BOOK_MAP_SAVE:-0}" == "1" ]]; then
  # slam_toolbox SaveMap explicitly loads nav2_map_server at service call time;
  # the earlier EKF/SLAM-only scope did not need this package.
  ADDONS+=(ros-jazzy-nav2-map-server)
fi
NEED_INSTALL=0
if ! test -x /opt/ros/jazzy/lib/robot_localization/ekf_node || \
   ! test -x /opt/ros/jazzy/lib/slam_toolbox/async_slam_toolbox_node; then
  NEED_INSTALL=1
fi
if [[ "${BOOK_MAP_SAVE:-0}" == "1" ]] && \
   ! test -f /opt/ros/jazzy/share/nav2_map_server/package.xml; then
  NEED_INSTALL=1
fi
if [[ "$NEED_INSTALL" == 1 ]]; then
  echo "INSTALL_EPHEMERAL_APT ${ADDONS[*]}" | tee -a "$OUT/addons_stage.txt"
  export DEBIAN_FRONTEND=noninteractive
  timeout --signal=TERM --kill-after=8s 105s apt-get update -qq > "$OUT/apt_update.log" 2>&1
  timeout --signal=TERM --kill-after=8s 120s \
    apt-get install -y --no-install-recommends "${ADDONS[@]}" \
    > "$OUT/apt_install.log" 2>&1
fi
dpkg-query -W "${ADDONS[@]}" > "$OUT/addon_versions.txt"
echo "ENVIRONMENT_ADDONS_READY" | tee -a "$OUT/addons_stage.txt"
exec bash /work/ci/docker/next_scope.sh Ch11
