// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include <dlfcn.h>
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <future>
#include <mutex>
#include <thread>
#include <vector>
#include "snapshot_camera_plugin.hpp"

using namespace std::chrono_literals;
using integrated_robot_camera::SnapshotCameraPlugin;

namespace
{
// Interpose the real native readback at the executable boundary, not a fake
// renderer or a test-only production method. The actual driver call still runs.
struct ReadbackBarrier
{
  std::mutex mutex;
  std::condition_variable cv;
  bool armed{false};
  bool entered{false};
  bool released{false};
  size_t calls{0};
  void arm()
  {
    std::lock_guard<std::mutex> lock(mutex);
    armed = true;
    entered = released = false;
    calls = 0;
  }
  bool wait()
  {
    std::unique_lock<std::mutex> lock(mutex);
    return cv.wait_for(lock, 10s, [&] {return entered;});
  }
  void release()
  {
    std::lock_guard<std::mutex> lock(mutex);
    released = true;
    armed = false;
    cv.notify_all();
  }
} readback;
}  // namespace

extern "C" void mjr_readPixels(unsigned char * rgb, float * depth, mjrRect viewport,
  const mjrContext * context)
{
  {
    std::unique_lock<std::mutex> lock(readback.mutex);
    ++readback.calls;
    if (readback.armed) {
      readback.entered = true;
      readback.cv.notify_all();
      readback.cv.wait(lock, [] {return readback.released;});
    }
  }
  using ReadPixels = void (*)(unsigned char *, float *, mjrRect, const mjrContext *);
  static const auto native = reinterpret_cast<ReadPixels>(dlsym(RTLD_NEXT, "mjr_readPixels"));
  if (!native) {std::abort();}
  native(rgb, depth, viewport, context);
}

namespace
{
class CameraTest : public ::testing::Test
{
protected:
  static void SetUpTestSuite() {rclcpp::init(0, nullptr);}
  static void TearDownTestSuite() {rclcpp::shutdown();}
  void SetUp() override
  {
    constexpr char xml[] = R"(<mujoco><visual><global offwidth="320" offheight="240"/></visual>
      <worldbody><light pos="0 0 2"/><geom type="plane" size="2 2 .1"/>
      <camera name="eye" pos="0 0 1" resolution="320 240" fovy="45"/>
      <camera name="other" pos="0 0 1" resolution="320 240"/>
      <body pos=".1 .1 .1"><joint type="slide" axis="1 0 0"/>
      <geom type="sphere" size=".08" mass="1" rgba="1 0 0 1"/></body>
      </worldbody></mujoco>)";
    mjVFS vfs;
    mj_defaultVFS(&vfs);
    ASSERT_EQ(mj_addBufferVFS(&vfs, "camera.xml", xml, sizeof(xml)), 0);
    char error[1024]{};
    model.reset(mj_loadXML("camera.xml", &vfs, error, sizeof(error)));
    mj_deleteVFS(&vfs);
    ASSERT_NE(model, nullptr) << error;
    data.reset(mj_makeData(model.get()));
    node = rclcpp::Node::make_shared("snapshot_camera_test");
    plugin_node = node->create_sub_node("eye_camera");
    node->declare_parameter("mujoco_plugins.eye_camera.camera_publish_rate", 1000000.);
    node->declare_parameter("mujoco_plugins.eye_camera.eye.policy", "streaming");
    node->declare_parameter("mujoco_plugins.eye_camera.other.policy", "disabled");
    node->declare_parameter("mujoco_plugins.eye_camera.eye.frame_name", "camera_optical_frame");
    rgb_sub = node->create_subscription<sensor_msgs::msg::Image>("/eye_camera/eye/color", 10,
      [this](sensor_msgs::msg::Image::ConstSharedPtr msg) {rgb.push_back(*msg);});
    depth_sub = node->create_subscription<sensor_msgs::msg::Image>("/eye_camera/eye/depth", 10,
      [this](sensor_msgs::msg::Image::ConstSharedPtr msg) {depth.push_back(*msg);});
    info_sub = node->create_subscription<sensor_msgs::msg::CameraInfo>("/eye_camera/eye/camera_info", 10,
      [this](sensor_msgs::msg::CameraInfo::ConstSharedPtr msg) {info.push_back(*msg);});
    executor.add_node(node);
  }
  void TearDown() override
  {
    readback.release();
    plugin.cleanup();
    executor.remove_node(node);
  }
  bool until(const std::function<bool()> & predicate, std::chrono::milliseconds timeout = 5s)
  {
    const auto deadline = std::chrono::steady_clock::now() + timeout;
    while (std::chrono::steady_clock::now() < deadline) {
      executor.spin_some();
      if (predicate()) {return true;}
      std::this_thread::sleep_for(2ms);
    }
    return false;
  }
  bool start()
  {
    return plugin.init(plugin_node, model.get(), data.get());
  }
  void frame(double stamp)
  {
    data->time = stamp;
    mj_forward(model.get(), data.get());
    plugin.update(model.get(), data.get());
  }
  void capture(double stamp)
  {
    const auto deadline = std::chrono::steady_clock::now() + 10s;
    while (std::chrono::steady_clock::now() < deadline) {
      frame(stamp);
      {
        std::lock_guard<std::mutex> lock(readback.mutex);
        if (readback.entered) {return;}
      }
      std::this_thread::sleep_for(2ms);
    }
    FAIL() << "real GL worker did not reach readback";
  }
  void poll(const std::string & camera = "eye")
  {
    auto client = node->create_client<std_srvs::srv::Trigger>("/eye_camera/" + camera + "/trigger");
    ASSERT_TRUE(client->wait_for_service(2s));
    auto future = client->async_send_request(std::make_shared<std_srvs::srv::Trigger::Request>());
    ASSERT_TRUE(until([&] {return future.wait_for(0s) == std::future_status::ready;}));
    EXPECT_TRUE(future.get()->success);
  }

  std::unique_ptr<mjModel, decltype(&mj_deleteModel)> model{nullptr, mj_deleteModel};
  std::unique_ptr<mjData, decltype(&mj_deleteData)> data{nullptr, mj_deleteData};
  SnapshotCameraPlugin plugin;
  rclcpp::Node::SharedPtr node, plugin_node;
  rclcpp::executors::SingleThreadedExecutor executor;
  rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr rgb_sub, depth_sub;
  rclcpp::Subscription<sensor_msgs::msg::CameraInfo>::SharedPtr info_sub;
  std::vector<sensor_msgs::msg::Image> rgb, depth;
  std::vector<sensor_msgs::msg::CameraInfo> info;
};

TEST_F(CameraTest, FrameHeadersMatchAcquiredSnapshot)
{
  ASSERT_TRUE(start());
  readback.arm();
  capture(1.);
  ASSERT_TRUE(readback.wait());
  frame(2.);  // real producer runs while native readback of the acquired frame is held
  readback.release();
  ASSERT_TRUE(until([&] {return !rgb.empty() && !depth.empty() && !info.empty();}));
  EXPECT_EQ(rgb.front().header.stamp, depth.front().header.stamp);
  EXPECT_EQ(rgb.front().header.stamp, info.front().header.stamp);
  EXPECT_EQ(rclcpp::Time(rgb.front().header.stamp).nanoseconds(), 1000000000LL);
  EXPECT_EQ(rgb.front().header.frame_id, "camera_optical_frame");
  EXPECT_EQ(rgb.front().width, 320u);
  EXPECT_EQ(rgb.front().height, 240u);
  EXPECT_EQ(depth.front().encoding, "32FC1");
  float center_depth;
  std::memcpy(&center_depth, &depth.front().data[(120 * 320 + 160) * 4], 4);
  EXPECT_NEAR(center_depth, 1., .02);  // plane is 1 meter below the camera
  double sum_u = 0., sum_v = 0.;
  size_t red = 0;
  for (size_t v = 0; v < 240; ++v) {
    for (size_t u = 0; u < 320; ++u) {
      const auto i = (v * 320 + u) * 3;
      if (rgb.front().data[i] > 100 && rgb.front().data[i + 1] < 50) {
        sum_u += u; sum_v += v; ++red;
      }
    }
  }
  ASSERT_GT(red, 10u);
  EXPECT_GT(sum_u / red, 160.);  // positive model X projects right
  EXPECT_LT(sum_v / red, 120.);  // positive model Y projects up after vertical flip
}

TEST_F(CameraTest, DisabledCameraNeverRenders)
{
  node->set_parameter(rclcpp::Parameter("mujoco_plugins.eye_camera.eye.policy", "disabled"));
  ASSERT_TRUE(start());
  readback.arm();
  for (size_t i = 0; i < 10; ++i) {frame(i * .1);}
  plugin.cleanup();
  std::lock_guard<std::mutex> lock(readback.mutex);
  EXPECT_EQ(readback.calls, 0u);
  EXPECT_EQ(node->count_publishers("/eye_camera/eye/color"), 0u);
}

TEST_F(CameraTest, PolledRequestsCoalesceWithLatestSnapshot)
{
  node->set_parameter(rclcpp::Parameter("mujoco_plugins.eye_camera.eye.policy", "polled"));
  ASSERT_TRUE(start());
  // Services exist before the first producer snapshot; repeated requests coalesce.
  poll(); poll();
  readback.arm();
  capture(1.);
  ASSERT_TRUE(readback.wait());
  poll(); frame(2.);
  poll(); frame(3.);
  readback.release();
  ASSERT_TRUE(until([&] {return rgb.size() >= 2;}));
  plugin.cleanup();
  until([] {return false;}, 100ms);
  ASSERT_EQ(rgb.size(), 2u);
  EXPECT_EQ(rclcpp::Time(rgb.back().header.stamp).nanoseconds(), 3000000000LL);
}

TEST_F(CameraTest, CleanupDuringInitializationAndRender)
{
  ASSERT_TRUE(start());
  plugin.cleanup();
  plugin.cleanup();
  ASSERT_TRUE(start());
  readback.arm();
  capture(1.);
  ASSERT_TRUE(readback.wait());
  auto cleanup = std::async(std::launch::async, [&] {plugin.cleanup();});
  EXPECT_EQ(cleanup.wait_for(50ms), std::future_status::timeout);
  readback.release();
  EXPECT_EQ(cleanup.wait_for(10s), std::future_status::ready);
  cleanup.get();
  plugin.cleanup();
}

// A streaming-only overwrite must not erase a still-unconsumed polled request.
TEST_F(CameraTest, StreamingOverwritePreservesPendingPollWithoutRepeatingIt)
{
  node->set_parameter(rclcpp::Parameter("mujoco_plugins.eye_camera.other.policy", "polled"));
  std::vector<sensor_msgs::msg::Image> polled;
  auto other = node->create_subscription<sensor_msgs::msg::Image>("/eye_camera/other/color", 10,
    [&](sensor_msgs::msg::Image::ConstSharedPtr msg) {polled.push_back(*msg);});
  ASSERT_TRUE(start());
  readback.arm();
  capture(1.);
  ASSERT_TRUE(readback.wait());
  poll("other"); frame(2.);
  frame(3.);  // no new trigger, but the pending request has not been rendered
  readback.release();
  EXPECT_TRUE(until([&] {return polled.size() == 1;}));
  if (!polled.empty()) {
    EXPECT_EQ(rclcpp::Time(polled.front().header.stamp).nanoseconds(), 3000000000LL);
  }
  frame(4.);
  until([] {return false;}, 100ms);
  EXPECT_EQ(polled.size(), 1u);
}

TEST_F(CameraTest, ResetDiscardsAcquiredOldEpochBeforePublish)
{
  ASSERT_TRUE(start());
  readback.arm();
  capture(1.);
  ASSERT_TRUE(readback.wait());
  plugin.on_reset(data.get());
  readback.release();
  // Do not stop first: stop alone could hide a missing reset invalidation.
  until([] {return false;}, 200ms);
  EXPECT_TRUE(rgb.empty());
  EXPECT_TRUE(depth.empty());
  EXPECT_TRUE(info.empty());
}

TEST_F(CameraTest, InvalidPolicyFailsClosedAndCleanupIsRepeatable)
{
  node->set_parameter(rclcpp::Parameter("mujoco_plugins.eye_camera.eye.policy", "invalid"));
  EXPECT_FALSE(start());
  frame(1.);
  plugin.cleanup();
  plugin.cleanup();
}
}  // namespace
