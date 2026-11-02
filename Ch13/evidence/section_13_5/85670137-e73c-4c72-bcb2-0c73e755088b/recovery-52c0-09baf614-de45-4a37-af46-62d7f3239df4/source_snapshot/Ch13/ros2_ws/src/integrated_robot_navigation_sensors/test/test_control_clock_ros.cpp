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
        if (row.at("event") == "publish" && sink_delay.count() > 0) {
          std::this_thread::sleep_for(sink_delay);
        }
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
  std::chrono::milliseconds sink_delay{0};
};

TEST_F(RelayRig, TraceWorkDoesNotAddItsDurationToEveryPublicationPeriod)
{
  // Controlled sink load exposes a structural timer-reset delay. It is NOT
  // a claim that the failed engine's actual file write took exactly 5ms.
  sink_delay = 5ms;
  const auto started = std::chrono::steady_clock::now();
  const auto until = started + 1500ms;
  std::exception_ptr input_error;
  std::thread input([&] {
      try {
        auto due = started;
        while (std::chrono::steady_clock::now() < until) {
          const auto capture = 123000000000LL + static_cast<int64_t>(++sequence)*2000000;
          rosgraph_msgs::msg::Clock msg;
          msg.clock.sec = static_cast<int32_t>(capture/1000000000);
          msg.clock.nanosec = static_cast<uint32_t>(capture%1000000000);
          sent.insert(capture);source->publish(msg);
          due += 2ms;std::this_thread::sleep_until(due);
        }
      } catch (...) {input_error = std::current_exception();}
    });
  while (std::chrono::steady_clock::now() < until) {executor->spin_some();}
  input.join();
  ASSERT_FALSE(input_error);
  size_t published = 0;
  int64_t previous = -1;
  const auto end_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(until.time_since_epoch()).count();
  for (const auto & row : rows) {
    if (row.at("event") != "publish") {continue;}
    const auto wall = row.at("published_wall_ns").get<int64_t>();
    if (wall < end_ns) {++published;}
    if (previous >= 0) {EXPECT_GE(wall-previous, 10000000);}
    EXPECT_EQ(sent.count(row.at("capture_ns").get<int64_t>()), 1u);
    previous = wall;
  }
  EXPECT_GE(published, 120u) << "10ms deadline was restarted AFTER every 5ms trace operation";
  EXPECT_TRUE(relay->report().at("fault").get<std::string>().empty());
}

TEST_F(RelayRig, ClosedTraceKeepsOriginalInputReceiptAndSeparateClockDomains)
{
  pump(100ms, true);
  relay->finish();
  const auto closed = std::find_if(rows.begin(), rows.end(), [](const auto & row) {
      return row.at("event") == "closed";
    });
  ASSERT_NE(closed, rows.end());
  ASSERT_TRUE(closed->contains("input_transport"));
  const auto & transport = closed->at("input_transport");
  EXPECT_EQ(transport.at("capacity"), 4096u);
  ASSERT_FALSE(transport.at("rows").empty());
  uint64_t previous = 0;
  for (const auto & receipt : transport.at("rows")) {
    EXPECT_GT(receipt.at("sequence").template get<uint64_t>(), previous);
    previous = receipt.at("sequence").template get<uint64_t>();
    EXPECT_EQ(sent.count(receipt.at("capture_ns").template get<int64_t>()), 1u);
    EXPECT_GT(receipt.at("received_wall_ns").template get<int64_t>(), 0);
    EXPECT_GT(receipt.at("callback_system_ns").template get<int64_t>(), 0);
    EXPECT_GT(receipt.at("source_system_ns").template get<int64_t>(), 0);
    EXPECT_GT(receipt.at("rmw_received_system_ns").template get<int64_t>(), 0);
    EXPECT_GE(receipt.at("raw_after_ns").template get<int64_t>(),
      receipt.at("raw_before_ns").template get<int64_t>());
  }
  ASSERT_TRUE(closed->contains("publication_work"));
  const auto & work = closed->at("publication_work");
  EXPECT_EQ(work.at("capacity"), 2048u);
  ASSERT_FALSE(work.at("rows").empty());
  int64_t previous_finish = -1;
  for (const auto & span : work.at("rows")) {
    const auto started = span.at("publish_started_wall_ns").template get<int64_t>();
    const auto finished = span.at("publish_finished_wall_ns").template get<int64_t>();
    EXPECT_GE(started, span.at("poll_wall_ns").template get<int64_t>());
    EXPECT_GE(finished, started);
    EXPECT_GE(span.at("trace_started_wall_ns").template get<int64_t>(), finished);
    EXPECT_GE(span.at("trace_finished_wall_ns").template get<int64_t>(),
      span.at("trace_started_wall_ns").template get<int64_t>());
    if (previous_finish >= 0) {EXPECT_GE(started-previous_finish, 10000000);}
    previous_finish = finished;
  }
  const auto before = received.size();
  pump(40ms, true);
  EXPECT_EQ(received.size(), before);
}

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
