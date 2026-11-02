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
    constexpr auto id = "integrated_robot_navigation_sensors/NativeNavigationSensorsPlugin";
    auto instance = loader.createSharedInstance(id);
    const auto path = std::filesystem::canonical(loader.getClassLibraryPath(id));
    if (!std::filesystem::is_regular_file(path) || mj_version() != mjVERSION_HEADER) {return 1;}
    std::cout << "{\"library\":\"" << path.string() << "\",\"mujoco_header\":"
              << mjVERSION_HEADER << ",\"mujoco_library\":" << mj_version() << "}\n";
    return 0;
  } catch (const std::exception & e) {std::cerr << e.what() << '\n'; return 1;}
}
