// SPDX-License-Identifier: Apache-2.0
// Breaks: relay retags time, forwards faster than100Hz, loses real publisher
// identity, resumes after pause/fault, or publishes after acknowledged stop.
#include <gtest/gtest.h>
#include "integrated_robot_navigation_sensors/control_clock_relay.hpp"
#include <algorithm>
#include <chrono>
#include <iomanip>
#include <set>
#include <sstream>
#include <thread>
using namespace std::chrono_literals;
using integrated_robot_navigation_sensors::ControlClockRelay;

class RelayRig : public ::testing::Test
{
protected:
  void SetUp() override
  {
    rclcpp::init(0, nullptr);
    executor = std::make_unique<rclcpp::executors::SingleThreadedExecutor>();
    rclcpp::NodeOptions options;
    options.arguments({"--ros-args", "-r", "/clock:=/clock_test/input",
      "-r", "/navigation/control_clock:=/clock_test/output"});
    relay = std::make_shared<ControlClockRelay>([this](const nlohmann::json & row) {
        rows.push_back(row);
      }, options);
    peer = std::make_shared<rclcpp::Node>("clock_test_peer");
    source = peer->create_publisher<rosgraph_msgs::msg::Clock>("/clock_test/input",
      rclcpp::QoS(1).best_effort());
    subscription = peer->create_subscription<rosgraph_msgs::msg::Clock>("/clock_test/output",
      rclcpp::QoS(100).best_effort(), [this](rosgraph_msgs::msg::Clock::ConstSharedPtr msg) {
        received.push_back(static_cast<int64_t>(msg->clock.sec)*1000000000+msg->clock.nanosec);
      });
    executor->add_node(relay); executor->add_node(peer);
    pump(150ms);  // DDS discovery, no positive source progress yet
  }
  void TearDown() override
  {
    executor->remove_node(relay); executor->remove_node(peer);
    subscription.reset(); source.reset(); relay.reset(); peer.reset();
    executor.reset();
    rclcpp::shutdown();
  }
  void pump(std::chrono::milliseconds duration, bool publish=false)
  {
    auto until = std::chrono::steady_clock::now()+duration;
    while (std::chrono::steady_clock::now() < until) {
      if (publish) {
        rosgraph_msgs::msg::Clock msg;
        msg.clock.sec = 123; msg.clock.nanosec = ++sequence*2000000;
        sent.insert(123000000000LL+msg.clock.nanosec);
        source->publish(msg);
      }
      executor->spin_some(); std::this_thread::sleep_for(2ms);
    }
  }
  std::shared_ptr<ControlClockRelay> relay;
  std::shared_ptr<rclcpp::Node> peer;
  rclcpp::Publisher<rosgraph_msgs::msg::Clock>::SharedPtr source;
  rclcpp::Subscription<rosgraph_msgs::msg::Clock>::SharedPtr subscription;
  std::unique_ptr<rclcpp::executors::SingleThreadedExecutor> executor;
  std::vector<nlohmann::json> rows;
  std::vector<int64_t> received;
  std::set<int64_t> sent;
  uint32_t sequence{0};
};

TEST_F(RelayRig, WireOutputsAreUnchangedSourceSubsetWithBoundedPublicationCadence)
{
  pump(350ms, true); pump(30ms);
  ASSERT_GE(received.size(), 10u);
  EXPECT_LT(received.size(), sent.size());
  EXPECT_TRUE(relay->report().at("fault").get<std::string>().empty());
  for (auto stamp : received) {EXPECT_EQ(sent.count(stamp), 1u);}
  int64_t previous = -1;
  std::ostringstream expected_gid;
  const auto source_gid = source->get_gid();
  for (auto byte : source_gid.data) {
    expected_gid << std::hex << std::setfill('0') << std::setw(2) << static_cast<unsigned>(byte);
  }
  for (const auto & row : rows) {
    if (row.at("event") != "publish") {continue;}
    const auto wall = row.at("published_wall_ns").get<int64_t>();
    if (previous >= 0) {EXPECT_GE(wall-previous, 10000000);}
    EXPECT_LE(wall-row.at("received_wall_ns").get<int64_t>(), 200000000);
    EXPECT_EQ(row.at("gid"), expected_gid.str());  // independent real publisher identity
    EXPECT_EQ(sent.count(row.at("capture_ns").get<int64_t>()), 1u);
    previous = wall;
  }
}

TEST_F(RelayRig, PauseLatchesFaultAndSourceResumeCannotReactivate)
{
  pump(100ms, true);
  auto client = peer->create_client<std_srvs::srv::Trigger>("/navigation_control_clock/arm");
  ASSERT_TRUE(client->wait_for_service(1s));
  auto future = client->async_send_request(std::make_shared<std_srvs::srv::Trigger::Request>());
  ASSERT_EQ(executor->spin_until_future_complete(future, 1s), rclcpp::FutureReturnCode::SUCCESS);
  ASSERT_TRUE(future.get()->success);
  pump(260ms);
  EXPECT_EQ(relay->report().at("fault"), "source_stalled");
  auto before = received.size();
  pump(100ms, true);
  EXPECT_EQ(received.size(), before);
}

TEST_F(RelayRig, BootstrapPauseBeforeArmingDoesNotLatchOperationalFault)
{
  pump(50ms, true); pump(260ms);
  EXPECT_FALSE(relay->report().at("armed"));
  EXPECT_EQ(relay->report().at("fault"), "");
  auto before = received.size();
  pump(100ms, true);
  EXPECT_GT(received.size(), before);
}

TEST_F(RelayRig, StopServiceClosesOutstandingWorkBeforeAcknowledging)
{
  pump(100ms, true);
  auto client = peer->create_client<std_srvs::srv::Trigger>("/navigation_control_clock/stop");
  ASSERT_TRUE(client->wait_for_service(1s));
  auto future = client->async_send_request(std::make_shared<std_srvs::srv::Trigger::Request>());
  ASSERT_EQ(executor->spin_until_future_complete(future, 1s), rclcpp::FutureReturnCode::SUCCESS);
  EXPECT_TRUE(future.get()->success);
  pump(30ms);  // drain already transmitted messages, not new publications
  const auto before = relay->report().at("outputs");
  pump(100ms, true);
  EXPECT_TRUE(relay->report().at("closing"));
  EXPECT_EQ(relay->report().at("outputs"), before);
}

TEST_F(RelayRig, CompetingDestinationOwnerFailsWithoutForwarding)
{
  auto competing = peer->create_publisher<rosgraph_msgs::msg::Clock>("/clock_test/output", 1);
  pump(100ms);
  EXPECT_EQ(relay->report().at("fault"), "destination_count");
  pump(100ms, true);
  EXPECT_TRUE(received.empty());
}
