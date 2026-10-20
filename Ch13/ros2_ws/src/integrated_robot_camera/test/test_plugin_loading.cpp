// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include <filesystem>
#include <pluginlib/class_loader.hpp>
#include "mujoco_ros2_control_plugins/mujoco_ros2_control_plugins_base.hpp"

TEST(PluginLoading, DistinctSnapshotAndUpstreamClassesRemainAvailable)
{
  pluginlib::ClassLoader<mujoco_ros2_control_plugins::MuJoCoROS2ControlPluginBase> loader(
    "mujoco_ros2_control_plugins", "mujoco_ros2_control_plugins::MuJoCoROS2ControlPluginBase");
  auto snapshot = loader.createSharedInstance("integrated_robot_camera/SnapshotCameraPlugin");
  ASSERT_NE(snapshot, nullptr);
  const auto library = loader.getClassLibraryPath("integrated_robot_camera/SnapshotCameraPlugin");
  EXPECT_TRUE(std::filesystem::path(library).is_absolute());
  EXPECT_TRUE(std::filesystem::is_regular_file(library));
  EXPECT_NE(library.find("integrated_robot_camera/lib/"), std::string::npos);
  auto original = loader.createSharedInstance("mujoco_ros2_control_plugins/CameraPlugin");
  ASSERT_NE(original, nullptr);
  EXPECT_NE(library, loader.getClassLibraryPath("mujoco_ros2_control_plugins/CameraPlugin"));
}
