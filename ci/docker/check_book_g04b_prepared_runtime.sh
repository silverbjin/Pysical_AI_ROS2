#!/usr/bin/env bash
# Read-only prepared-image dependency contract. No ROS Goal, Gazebo or network.
set -Eeuo pipefail
test -f /opt/ros/jazzy/setup.bash
test "$(. /etc/os-release;printf '%s' "$VERSION_CODENAME")" = noble
pkgs=(
  ros-jazzy-moveit-configs-utils
  ros-jazzy-moveit-planners-ompl
  ros-jazzy-moveit-simple-controller-manager
  ros-jazzy-moveit-kinematics
  ros-jazzy-moveit-ros-move-group
  ros-jazzy-moveit-msgs
  ros-jazzy-gz-ros2-control
  ros-jazzy-controller-manager ros-jazzy-ros2controlcli
  ros-jazzy-joint-trajectory-controller ros-jazzy-joint-state-broadcaster
  ros-jazzy-ros2-control ros-jazzy-robot-state-publisher
  ros-jazzy-xacro ros-jazzy-control-msgs
  libgz-sim8-dev libgz-plugin2-dev cmake g++ pkg-config
)
for pkg in "${pkgs[@]}";do
  dpkg-query -W -f='${Status}\n' "$pkg" 2>/dev/null | grep -qx 'install ok installed' || {
    echo "G04B_RUNTIME_MISSING_PACKAGE=$pkg" >&2
    exit 32
  }
done
# Pure package inventory only. Do not launch a simulation in the image build.
dpkg-query -W "${pkgs[@]}"
echo G04B_PREPARED_IMAGE_DEPENDENCIES_VERIFIED_NO_GAZEBO
