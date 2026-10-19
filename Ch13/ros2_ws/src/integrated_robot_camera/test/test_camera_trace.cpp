// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include <chrono>
#include <thread>
#include <dlfcn.h>
#include <optional>
#include <cstring>
#include <rcl/publisher.h>
#include <rcl/error_handling.h>
#include "camera_trace.hpp"

using namespace integrated_robot_camera;
namespace
{
std::optional<rmw_qos_profile_t> actual_qos;
bool reject_trace_publication = false;
}

// Inspect the actual live publisher rather than FastDDS graph discovery:
// the installed Jazzy qos.hpp explicitly omits discovered history/depth.
extern "C" rcl_ret_t rcl_publish(const rcl_publisher_t * publisher,
  const void * message, rmw_publisher_allocation_t * allocation)
{
  if (std::strcmp(rcl_publisher_get_topic_name(publisher), "/vision/camera_trace") == 0) {
    if (const auto * qos = rcl_publisher_get_actual_qos(publisher)) {actual_qos = *qos;}
    if (reject_trace_publication) {
      RCL_SET_ERROR_MSG("test transport failure, not a renderer failure");
      return RCL_RET_ERROR;
    }
  }
  using Publish = decltype(&rcl_publish);
  static const auto native = reinterpret_cast<Publish>(dlsym(RTLD_NEXT, "rcl_publish"));
  if (!native) {std::abort();}
  return native(publisher, message, allocation);
}

namespace
{
constexpr char run[] = "424240ff-0bfe-4a4b-92d4-93f6a78d49b8";
class TraceTest : public ::testing::Test
{
protected:
  static void SetUpTestSuite() {rclcpp::init(0, nullptr);}
  static void TearDownTestSuite() {rclcpp::shutdown();}
  rclcpp::Node::SharedPtr node = rclcpp::Node::make_shared("camera_trace_test");
  NativeFrameTrace frame()
  {
    NativeFrameTrace value;
    value.source_frame = "camera_optical_frame";
    value.capture_ns = 1234567890;
    value.local_epoch = 2;
    value.native_sequence = 7;
    value.ros_now_ns = 1400000000;
    uint64_t time = 10;
    for (const auto key : native_trace_keys) {value.times_ns[key] = time++;}
    return value;
  }
};

TEST_F(TraceTest, TraceDisabledNeverPublishes)
{
  CameraTrace trace(node, false, "");
  EXPECT_EQ(node->count_publishers("/vision/camera_trace"), 0u);
  EXPECT_FALSE(trace.publish(frame()));
  EXPECT_EQ(trace.stats().attempted, 0u);
}

TEST_F(TraceTest, TraceEscapesStringsAndCapsUtf8Bytes)
{
  std::string received;
  auto sub = node->create_subscription<std_msgs::msg::String>("/vision/camera_trace",
    rclcpp::SensorDataQoS().keep_last(32),
    [&](std_msgs::msg::String::ConstSharedPtr msg) {received = msg->data;});
  CameraTrace trace(node, true, run);
  auto value = frame();
  value.source_frame = "cam\"\\\n한글";
  ASSERT_TRUE(trace.publish(value));
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
  while (received.empty() && std::chrono::steady_clock::now() < deadline) {
    rclcpp::spin_some(node);
    std::this_thread::sleep_for(std::chrono::milliseconds(2));
  }
  ASSERT_FALSE(received.empty());
  EXPECT_NE(received.find("cam\\\"\\\\\\n한글"), std::string::npos);
  EXPECT_NE(received.find("\"clock_id\":\"linux/CLOCK_MONOTONIC\""), std::string::npos);
  EXPECT_NE(received.find("\"capture_ns\":1234567890"), std::string::npos);
  EXPECT_LE(received.size(), 4096u);
  value.source_frame = std::string(4096, '\1');  // escaping expands byte size
  EXPECT_FALSE(trace.publish(value));
  EXPECT_EQ(trace.stats().oversize, 1u);
  EXPECT_EQ(trace.stats().dropped, 1u);
  value = frame();
  value.times_ns["acquire"] = 0;  // a failed clock read cannot masquerade as valid
  EXPECT_FALSE(trace.publish(value));
  EXPECT_EQ(trace.stats().errors, 1u);
  EXPECT_EQ(trace.stats().dropped, 2u);
  const auto endpoints = node->get_publishers_info_by_topic("/vision/camera_trace");
  ASSERT_EQ(endpoints.size(), 1u);
  const auto qos = endpoints.front().qos_profile().get_rmw_qos_profile();
  EXPECT_EQ(qos.reliability, RMW_QOS_POLICY_RELIABILITY_BEST_EFFORT);
  EXPECT_EQ(qos.durability, RMW_QOS_POLICY_DURABILITY_VOLATILE);
  ASSERT_TRUE(actual_qos);
  EXPECT_EQ(actual_qos->history, RMW_QOS_POLICY_HISTORY_KEEP_LAST);
  EXPECT_EQ(actual_qos->depth, 32u);
  EXPECT_EQ(actual_qos->reliability, RMW_QOS_POLICY_RELIABILITY_BEST_EFFORT);
  EXPECT_EQ(actual_qos->durability, RMW_QOS_POLICY_DURABILITY_VOLATILE);
}

TEST_F(TraceTest, TransportFailureIsCountedAndContained)
{
  CameraTrace trace(node, true, run);
  reject_trace_publication = true;
  EXPECT_FALSE(trace.publish(frame()));
  reject_trace_publication = false;
  EXPECT_EQ(trace.stats().errors, 1u);
  EXPECT_EQ(trace.stats().dropped, 1u);
  EXPECT_EQ(trace.stats().emitted, 0u);
  EXPECT_TRUE(trace.publish(frame()));  // explicit next frame, not an automatic retry
}

TEST_F(TraceTest, TraceStopsAtSessionLimit)
{
  CameraTrace trace(node, true, run);
  for (size_t i = 0; i < 20000; ++i) {ASSERT_TRUE(trace.publish(frame()));}
  EXPECT_FALSE(trace.publish(frame()));
  EXPECT_EQ(trace.stats().attempted, 20001u);
  EXPECT_EQ(trace.stats().emitted, 20000u);
  EXPECT_EQ(trace.stats().dropped, 1u);
  EXPECT_EQ(trace.stats().errors, 0u);
}

TEST_F(TraceTest, InvalidRunIdRejected)
{
  EXPECT_THROW(CameraTrace(node, true, "invalid"), std::invalid_argument);
}
}  // namespace
