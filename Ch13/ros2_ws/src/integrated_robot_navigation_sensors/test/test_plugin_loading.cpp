// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include <pluginlib/class_loader.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <sensor_msgs/msg/laser_scan.hpp>
#include <integrated_robot_interfaces/msg/foot_contacts.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <chrono>
#include <vector>
#include <thread>
#include "fixture.hpp"
#include "mujoco_ros2_control_plugins/mujoco_ros2_control_plugins_base.hpp"

using Base = mujoco_ros2_control_plugins::MuJoCoROS2ControlPluginBase;
using namespace std::chrono_literals;

TEST(NativePlugin, RealRosMeasurementsReadOnlyAndResetFailClosed)
{
  if (!rclcpp::ok()) {rclcpp::init(0, nullptr);}
  auto node = std::make_shared<rclcpp::Node>("navigation_plugin_test");
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(node);
  pluginlib::ClassLoader<Base> loader("mujoco_ros2_control_plugins",
    "mujoco_ros2_control_plugins::MuJoCoROS2ControlPluginBase");
  auto plugin = loader.createSharedInstance(
    "integrated_robot_navigation_sensors/NativeNavigationSensorsPlugin");
  auto m = nav_test::model();
  auto d = nav_test::settled(m.get());
  const auto qos = rclcpp::SensorDataQoS();
  std::vector<integrated_robot_interfaces::msg::FootContacts> contacts;
  std::vector<sensor_msgs::msg::Imu> imu;
  std::vector<sensor_msgs::msg::LaserScan> scans;
  auto a = node->create_subscription<integrated_robot_interfaces::msg::FootContacts>(
    "/navigation/foot_contacts", qos,
    [&](integrated_robot_interfaces::msg::FootContacts::ConstSharedPtr msg) {contacts.push_back(*msg);});
  auto b = node->create_subscription<sensor_msgs::msg::Imu>(
    "/navigation/imu", qos, [&](sensor_msgs::msg::Imu::ConstSharedPtr msg) {imu.push_back(*msg);});
  auto c = node->create_subscription<sensor_msgs::msg::LaserScan>(
    "/scan", qos, [&](sensor_msgs::msg::LaserScan::ConstSharedPtr msg) {scans.push_back(*msg);});
  ASSERT_TRUE(plugin->init(node, m.get(), d.get()));
  const std::vector<mjtNum> before(d->qpos, d->qpos + m->nq);
  auto deadline = std::chrono::steady_clock::now() + 3s;
  while ((contacts.empty() || imu.empty() || scans.empty()) &&
    std::chrono::steady_clock::now() < deadline)
  {
    plugin->update(m.get(), d.get());
    executor.spin_some();
    std::this_thread::sleep_for(2ms);
    // Repeated capture must NOT be republished with a new header.
  }
  ASSERT_FALSE(contacts.empty()); ASSERT_FALSE(imu.empty()); ASSERT_FALSE(scans.empty());
  EXPECT_EQ(before, std::vector<mjtNum>(d->qpos, d->qpos + m->nq));
  EXPECT_EQ(contacts.back().header.frame_id, "odom");
  EXPECT_NEAR(rclcpp::Time(contacts.back().header.stamp).seconds(), 2., 1e-9);
  EXPECT_EQ(imu.back().header.frame_id, "base_link");
  EXPECT_NEAR(imu.back().linear_acceleration.z, 9.81, .05);
  EXPECT_EQ(scans.back().header.frame_id, "lidar_link");
  EXPECT_NEAR(scans.back().ranges.at(180), 1.9, .01);
  const size_t count = contacts.size();
  plugin->on_reset(d.get());
  for (int i = 0; i < 20; ++i) {
    mj_step(m.get(), d.get()); plugin->update(m.get(), d.get());
    executor.spin_some(); std::this_thread::sleep_for(2ms);
  }
  EXPECT_EQ(contacts.size(), count);
  auto stop = node->create_client<std_srvs::srv::Trigger>("/navigation/stop_native_sensors");
  ASSERT_TRUE(stop->wait_for_service(1s));
  auto future = stop->async_send_request(std::make_shared<std_srvs::srv::Trigger::Request>());
  EXPECT_EQ(executor.spin_until_future_complete(future, 2s), rclcpp::FutureReturnCode::SUCCESS);
  if (future.wait_for(0s) == std::future_status::ready) {EXPECT_TRUE(future.get()->success);}
  plugin->cleanup(); plugin.reset();
  executor.remove_node(node);
  rclcpp::shutdown();
}
