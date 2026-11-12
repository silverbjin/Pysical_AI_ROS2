# Shared ROS 2 Jazzy + Gazebo Harmonic verification runtime.
# Base tag NOT immutable until base manifest digest is separately pinned.
FROM ros:jazzy-ros-base-noble

ENV DEBIAN_FRONTEND=noninteractive     ROS_DISTRO=jazzy     QT_QPA_PLATFORM=offscreen     LIBGL_ALWAYS_SOFTWARE=1

RUN apt-get update && apt-get install -y --no-install-recommends     python3-colcon-common-extensions     python3-rosdep python3-pip python3-yaml liburdfdom-tools     ros-jazzy-ros-gz ros-jazzy-xacro ros-jazzy-robot-state-publisher     ros-jazzy-rviz2 ros-jazzy-joint-state-publisher-gui     ros-jazzy-tf2-ros ros-jazzy-tf2-tools     ros-jazzy-ros2-control ros-jazzy-ros2-controllers     ros-jazzy-gz-ros2-control ros-jazzy-controller-manager     ros-jazzy-trajectory-msgs ros-jazzy-geometry-msgs     ros-jazzy-sensor-msgs ros-jazzy-rosgraph-msgs ros-jazzy-std-msgs   && rm -rf /var/lib/apt/lists/*

WORKDIR /work
CMD ["bash"]
