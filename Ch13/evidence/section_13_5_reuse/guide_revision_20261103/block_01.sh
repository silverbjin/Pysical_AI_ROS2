. /etc/os-release
printf 'OS=%s %s\n' "$ID" "$VERSION_ID"
python3 --version

sudo apt update
sudo apt install git curl build-essential cmake \
  python3-venv python3-pip python3-colcon-common-extensions python3-pytest \
  libssl-dev libegl1 libgl1-mesa-dri \
  ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-tf2-tools

source /opt/ros/jazzy/setup.bash
ros2 pkg prefix nav2_bringup
ros2 pkg prefix nav2_regulated_pure_pursuit_controller
dpkg-query -W ros-jazzy-nav2-bringup ros-jazzy-nav2-controller \
  ros-jazzy-nav2-velocity-smoother
