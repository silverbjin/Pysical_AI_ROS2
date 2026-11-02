// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include <pluginlib/class_loader.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <sensor_msgs/msg/laser_scan.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <integrated_robot_interfaces/msg/foot_contacts.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <std_msgs/msg/string.hpp>
#include <nlohmann/json.hpp>
#include <chrono>
#include <cmath>
#include <vector>
#include <thread>
#include "fixture.hpp"
#include "mujoco_ros2_control_plugins/mujoco_ros2_control_plugins_base.hpp"

using Base = mujoco_ros2_control_plugins::MuJoCoROS2ControlPluginBase;
using namespace std::chrono_literals;

TEST(NativePlugin, AppliedReferenceIsActualPreStepAndNotCmSnapshot)
{
  if (!rclcpp::ok()) {rclcpp::init(0, nullptr);}
  auto node = std::make_shared<rclcpp::Node>("applied_reference_test");
  rclcpp::executors::SingleThreadedExecutor executor; executor.add_node(node);
  pluginlib::ClassLoader<Base> loader("mujoco_ros2_control_plugins",
    "mujoco_ros2_control_plugins::MuJoCoROS2ControlPluginBase");
  auto plugin = loader.createSharedInstance(
    "integrated_robot_navigation_sensors/NativeNavigationSensorsPlugin");
  auto model = nav_test::model(); auto staged = nav_test::settled(model.get());
  std::vector<sensor_msgs::msg::JointState> applied;
  auto sub = node->create_subscription<sensor_msgs::msg::JointState>(
    "/navigation/applied_reference", rclcpp::SensorDataQoS(),
    [&](sensor_msgs::msg::JointState::ConstSharedPtr msg) {applied.push_back(*msg);});
  ASSERT_TRUE(plugin->init(node,model.get(),staged.get()));
  staged->ctrl[0]=.456;plugin->update(model.get(),staged.get());
  executor.spin_some();EXPECT_TRUE(applied.empty());
  auto live=nav_test::settled(model.get());live->time=2.02;live->ctrl[0]=.789;
  const std::vector<mjtNum> original(live->qpos,live->qpos+model->nq);
  plugin->pre_step(live.get());
  auto deadline=std::chrono::steady_clock::now()+1s;
  while(applied.empty() && std::chrono::steady_clock::now()<deadline) {
    executor.spin_some();std::this_thread::sleep_for(2ms);
  }
  ASSERT_FALSE(applied.empty()) << "actual physics reference echo missing";
  const auto endpoints=node->get_publishers_info_by_topic("/navigation/applied_reference");
  ASSERT_EQ(endpoints.size(),1u);
  EXPECT_EQ(endpoints[0].qos_profile().reliability(),rclcpp::ReliabilityPolicy::Reliable);
  EXPECT_EQ(applied.back().header.frame_id,"mujoco/pre_step");
  EXPECT_EQ(rclcpp::Time(applied.back().header.stamp).nanoseconds(),2020000000LL);
  ASSERT_EQ(applied.back().name.size(),1u);
  EXPECT_EQ(applied.back().name[0],"diagnostic_joint");
  EXPECT_DOUBLE_EQ(applied.back().position[0],.789);
  EXPECT_EQ(original,std::vector<mjtNum>(live->qpos,live->qpos+model->nq));
  EXPECT_DOUBLE_EQ(live->ctrl[0],.789);
  const auto count=applied.size();live->time=2.04;plugin->pre_step(live.get());
  for(int i=0;i<20;++i) {executor.spin_some();std::this_thread::sleep_for(2ms);}
  EXPECT_EQ(applied.size(),count) << "unchanged reference retagged as a new application";
  // Match the fixed underlay publish_clock sec/fraction truncation exactly.
  // No tolerance or current-clock substitution may make a future ACK eligible.
  for(const double capture:{35.29,35.33,35.59,93.284}) {
    const auto before=applied.size();live->time=capture;live->ctrl[0]+=.001;
    plugin->pre_step(live.get());deadline=std::chrono::steady_clock::now()+1s;
    while(applied.size()==before && std::chrono::steady_clock::now()<deadline) {
      executor.spin_some();std::this_thread::sleep_for(2ms);
    }
    ASSERT_GT(applied.size(),before);
    const auto sec=static_cast<int32_t>(std::floor(capture));
    const auto ns=static_cast<uint32_t>((capture-sec)*1e9);
    EXPECT_EQ(rclcpp::Time(applied.back().header.stamp).nanoseconds(),
      static_cast<int64_t>(sec)*1000000000LL+ns) << "capture=" << capture;
    EXPECT_EQ(original,std::vector<mjtNum>(live->qpos,live->qpos+model->nq));
  }
  plugin->cleanup();plugin.reset();executor.remove_node(node);rclcpp::shutdown();
}

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
  d->ctrl[0] = .123;
  const auto qos = rclcpp::SensorDataQoS();
  std::vector<integrated_robot_interfaces::msg::FootContacts> contacts;
  std::vector<sensor_msgs::msg::Imu> imu;
  std::vector<sensor_msgs::msg::LaserScan> scans;
  std::vector<nlohmann::json> controls;
  auto a = node->create_subscription<integrated_robot_interfaces::msg::FootContacts>(
    "/navigation/foot_contacts", qos,
    [&](integrated_robot_interfaces::msg::FootContacts::ConstSharedPtr msg) {contacts.push_back(*msg);});
  auto b = node->create_subscription<sensor_msgs::msg::Imu>(
    "/navigation/imu", qos, [&](sensor_msgs::msg::Imu::ConstSharedPtr msg) {imu.push_back(*msg);});
  auto c = node->create_subscription<sensor_msgs::msg::LaserScan>(
    "/scan", qos, [&](sensor_msgs::msg::LaserScan::ConstSharedPtr msg) {scans.push_back(*msg);});
  auto diagnostic = node->create_subscription<std_msgs::msg::String>(
    "/navigation/native_controls", rclcpp::QoS(rclcpp::KeepLast(100)).reliable(),
    [&](std_msgs::msg::String::ConstSharedPtr msg) {
      controls.push_back(nlohmann::json::parse(msg->data));
    });
  ASSERT_TRUE(plugin->init(node, m.get(), d.get()));
  const std::vector<mjtNum> before(d->qpos, d->qpos + m->nq);
  auto deadline = std::chrono::steady_clock::now() + 3s;
  while ((contacts.empty() || imu.empty() || scans.empty() || controls.empty()) &&
    std::chrono::steady_clock::now() < deadline)
  {
    plugin->update(m.get(), d.get());
    executor.spin_some();
    std::this_thread::sleep_for(2ms);
    // Repeated capture must NOT be republished with a new header.
  }
  ASSERT_FALSE(contacts.empty()); ASSERT_FALSE(imu.empty()); ASSERT_FALSE(scans.empty());
  ASSERT_FALSE(controls.empty());
  EXPECT_EQ(controls.back().at("schema"), 1);
  EXPECT_EQ(controls.back().at("capture_ns"), 2000000000LL);
  EXPECT_EQ(controls.back().at("actuators")[0].at("joint_name"), "diagnostic_joint");
  EXPECT_DOUBLE_EQ(controls.back().at("actuators")[0].at("ctrl").get<double>(), .123);
  const auto & reference = controls.back().at("body_reference");
  EXPECT_EQ(reference.at("source"), "mujoco_free_joint_qvel");
  EXPECT_EQ(reference.at("frame_id"), "base_link");
  for (int i = 0; i < 3; ++i) {
    EXPECT_DOUBLE_EQ(reference.at("angular_velocity").at(i).get<double>(), d->qvel[3+i]);
  }
  EXPECT_EQ(before, std::vector<mjtNum>(d->qpos, d->qpos + m->nq));
  EXPECT_EQ(contacts.back().header.frame_id, "odom");
  EXPECT_NEAR(rclcpp::Time(contacts.back().header.stamp).seconds(), 2., 1e-9);
  EXPECT_EQ(imu.back().header.frame_id, "base_link");
  EXPECT_NEAR(imu.back().linear_acceleration.z, 9.81, .05);
  EXPECT_EQ(scans.back().header.frame_id, "lidar_link");
  EXPECT_NEAR(scans.back().ranges.at(180), 1.9, .01);
  // A write-cycle snapshot's time and staged ctrl must not be represented as
  // an actual physics application. Trace both boundaries without a new writer.
  d->ctrl[0] = .456;
  plugin->update(m.get(), d.get());
  auto live = nav_test::settled(m.get());
  live->time = 2.02; live->ctrl[0] = .789;
  const std::vector<mjtNum> live_q(live->qpos, live->qpos+m->nq);
  plugin->pre_step(live.get());
  EXPECT_DOUBLE_EQ(live->ctrl[0], .789);
  EXPECT_EQ(live_q, std::vector<mjtNum>(live->qpos, live->qpos+m->nq));
  auto trace_client = node->create_client<std_srvs::srv::Trigger>(
    "/navigation/native_command_trace");
  ASSERT_TRUE(trace_client->wait_for_service(500ms));
  auto trace_future = trace_client->async_send_request(
    std::make_shared<std_srvs::srv::Trigger::Request>());
  ASSERT_EQ(executor.spin_until_future_complete(trace_future, 3s), rclcpp::FutureReturnCode::SUCCESS);
  const auto trace_response = trace_future.get();
  ASSERT_TRUE(trace_response->success);
  const auto trace = nlohmann::json::parse(trace_response->message);
  ASSERT_TRUE(trace.at("frozen"));
  ASSERT_EQ(trace.at("joints")[0], "diagnostic_joint");
  EXPECT_EQ(trace.at("cm_write").at("rows").back().at("snapshot_ros_ns"), 2000000000LL);
  EXPECT_DOUBLE_EQ(trace.at("cm_write").at("rows").back().at("ctrl")[0].get<double>(), .456);
  EXPECT_EQ(trace.at("pre_step").at("rows").back().at("snapshot_ros_ns"), 2020000000LL);
  EXPECT_DOUBLE_EQ(trace.at("pre_step").at("rows").back().at("ctrl")[0].get<double>(), .789);
  EXPECT_EQ(trace.at("pre_step").at("dropped_busy"), 0);
  EXPECT_EQ(trace.at("cm_write").at("dropped_busy"), 0);
  EXPECT_GT(trace.at("pre_step").at("rows").back().at("steady_ns").get<int64_t>(), 0);
  plugin->pre_step(live.get());  // frozen trace must not resume implicitly
  auto again = trace_client->async_send_request(std::make_shared<std_srvs::srv::Trigger::Request>());
  ASSERT_EQ(executor.spin_until_future_complete(again, 3s), rclcpp::FutureReturnCode::SUCCESS);
  EXPECT_EQ(nlohmann::json::parse(again.get()->message), trace);
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
