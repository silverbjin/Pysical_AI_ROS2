// SPDX-License-Identifier: Apache-2.0
// Break: guessing TF authority from a Python API without per-message GIDs.
#include <gtest/gtest.h>
#include <rclcpp/rclcpp.hpp>
#include <tf2_msgs/msg/tf_message.hpp>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <thread>
#include <vector>
#include "integrated_robot_navigation_sensors/tf_provenance.hpp"

using namespace std::chrono_literals;

TEST(TfProvenance, NativeMessageIdentityRetainsParentAndPublisherChanges)
{
  if (!rclcpp::ok()) {rclcpp::init(0, nullptr);}
  std::vector<nlohmann::json> rows;
  auto observer = std::make_shared<integrated_robot_navigation_sensors::TfProvenanceObserver>(
    [&rows](const nlohmann::json & row) {rows.push_back(row);});
  auto a = std::make_shared<rclcpp::Node>("provenance_owner_a");
  auto b = std::make_shared<rclcpp::Node>("provenance_owner_b");
  auto first = a->create_publisher<tf2_msgs::msg::TFMessage>("/tf", 10);
  auto second = b->create_publisher<tf2_msgs::msg::TFMessage>("/tf", 10);
  const auto static_qos = rclcpp::QoS(1).transient_local();
  auto fixed = a->create_publisher<tf2_msgs::msg::TFMessage>("/tf_static", static_qos);
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(observer); executor.add_node(a); executor.add_node(b);
  tf2_msgs::msg::TFMessage msg;
  geometry_msgs::msg::TransformStamped transform;
  transform.header.frame_id = "odom"; transform.child_frame_id = "provenance_test_base";
  transform.header.stamp.sec = 123; transform.transform.rotation.w = 1.;
  msg.transforms.push_back(transform);
  auto wait_count = [&](size_t count, auto publish) {
      const auto deadline = std::chrono::steady_clock::now()+3s;
      while (rows.size() < count && std::chrono::steady_clock::now() < deadline) {
        publish(); executor.spin_some(); std::this_thread::sleep_for(5ms);
      }
    };
  wait_count(1, [&] {first->publish(msg);});
  ASSERT_EQ(rows.size(), 1u);
  EXPECT_EQ(rows[0].at("parent"), "odom");
  EXPECT_EQ(rows[0].at("child"), "provenance_test_base");
  EXPECT_EQ(rows[0].at("stamp_ns"), 123000000000LL);
  EXPECT_EQ(rows[0].at("topic"), "/tf");
  // Expected identity comes independently from the real publisher, not the observer.
  auto publisher_gid = first->get_gid();
  std::ostringstream expected;
  for (const auto byte : publisher_gid.data) {
    expected << std::hex << std::setfill('0') << std::setw(2) << static_cast<unsigned>(byte);
  }
  EXPECT_EQ(rows[0].at("gid"), expected.str());
  EXPECT_GT(rows[0].at("source_timestamp").get<int64_t>(), 0);
  for (int i = 0; i < 10; ++i) {first->publish(msg); executor.spin_some();}
  EXPECT_EQ(rows.size(), 1u);  // repeated poses cannot hide an owner/parent transition
  wait_count(2, [&] {second->publish(msg);});
  ASSERT_EQ(rows.size(), 2u);
  EXPECT_NE(rows[0].at("gid"), rows[1].at("gid"));
  msg.transforms[0].header.frame_id = "wrong_parent";
  wait_count(3, [&] {first->publish(msg);});
  ASSERT_EQ(rows.size(), 3u);
  EXPECT_EQ(rows[2].at("parent"), "wrong_parent");
  msg.transforms[0].child_frame_id = "provenance_test_sensor";
  wait_count(4, [&] {fixed->publish(msg);});
  ASSERT_EQ(rows.size(), 4u);
  EXPECT_EQ(rows[3].at("topic"), "/tf_static");
  executor.remove_node(observer); executor.remove_node(a); executor.remove_node(b);
  rclcpp::shutdown();
}
