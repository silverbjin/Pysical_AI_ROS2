// SPDX-License-Identifier: Apache-2.0
#include <filesystem>
#include <iostream>
#include <pluginlib/class_loader.hpp>
#include "mujoco_ros2_control_plugins/mujoco_ros2_control_plugins_base.hpp"

int main()
{
  try {
    pluginlib::ClassLoader<mujoco_ros2_control_plugins::MuJoCoROS2ControlPluginBase> loader(
      "mujoco_ros2_control_plugins", "mujoco_ros2_control_plugins::MuJoCoROS2ControlPluginBase");
    constexpr auto id = "integrated_robot_camera/SnapshotCameraPlugin";
    auto instance = loader.createSharedInstance(id);  // no init, ROS context, or GL operation
    const auto path = std::filesystem::canonical(loader.getClassLibraryPath(id));
    if (!std::filesystem::is_regular_file(path)) {return 1;}
    std::cout << path.string() << '\n';
    return 0;
  } catch (const std::exception & error) {
    std::cerr << "Snapshot camera probe failed: " << error.what() << '\n';
    return 1;
  }
}
