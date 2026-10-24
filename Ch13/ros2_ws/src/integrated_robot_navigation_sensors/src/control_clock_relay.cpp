// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/control_clock_relay.hpp"
#include <algorithm>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace integrated_robot_navigation_sensors
{
int64_t ControlClockRelay::wall_now()
{
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::steady_clock::now().time_since_epoch()).count();
}

ControlClockRelay::ControlClockRelay(std::function<void(const nlohmann::json &)> sink,
  const rclcpp::NodeOptions & options)
: Node("navigation_control_clock", options), sink_(std::move(sink))
{
  if (!sink_) {throw std::invalid_argument("control clock trace sink required");}
  if (get_parameter("use_sim_time").as_bool()) {
    throw std::invalid_argument("control clock relay must not use simulated time");
  }
  const auto qos = rclcpp::QoS(1).best_effort();
  output_ = create_publisher<rosgraph_msgs::msg::Clock>("/navigation/control_clock", qos);
  input_ = create_subscription<rosgraph_msgs::msg::Clock>("/clock", qos,
    [this](rosgraph_msgs::msg::Clock::ConstSharedPtr msg, const rclcpp::MessageInfo & info) {
      receive(*msg, info);
    });
  timer_ = create_wall_timer(std::chrono::milliseconds(10), [this] {tick();});
  report_ = create_service<std_srvs::srv::Trigger>("~/report",
    [this](const std_srvs::srv::Trigger::Request::SharedPtr,
    std_srvs::srv::Trigger::Response::SharedPtr response) {
      response->success = true; response->message = report().dump();
    });
  stop_ = create_service<std_srvs::srv::Trigger>("~/stop",
    [this](const std_srvs::srv::Trigger::Request::SharedPtr,
    std_srvs::srv::Trigger::Response::SharedPtr response) {
      finish(); response->success = gate_.fault().empty(); response->message = report().dump();
    });
  arm_ = create_service<std_srvs::srv::Trigger>("~/arm",
    [this](const std_srvs::srv::Trigger::Request::SharedPtr,
    std_srvs::srv::Trigger::Response::SharedPtr response) {
      if (count_publishers(input_->get_topic_name()) != 1 ||
          count_publishers(output_->get_topic_name()) != 1) {gate_.fail("arming_owner_count");}
      const bool already = gate_.armed();
      const auto wall = wall_now();
      response->success = gate_.arm(wall);
      response->message = report().dump();
      if (response->success && !already) {
        trace({{"event", "armed"}, {"wall_ns", wall}, {"report", report()}});
      }
    });
}

void ControlClockRelay::receive(const rosgraph_msgs::msg::Clock & msg, const rclcpp::MessageInfo & info)
{
  if (gate_.closing()) {return;}
  if (msg.clock.sec < 0 || msg.clock.nanosec >= 1000000000) {gate_.fail("invalid_stamp"); return;}
  const auto & bytes = info.get_rmw_message_info().publisher_gid.data;
  if (std::all_of(std::begin(bytes), std::end(bytes), [](auto byte) {return byte == 0;})) {
    gate_.fail("invalid_gid"); return;
  }
  std::ostringstream identity;
  for (auto byte : bytes) {
    identity << std::hex << std::setfill('0') << std::setw(2) << static_cast<unsigned>(byte);
  }
  gate_.receive(static_cast<int64_t>(msg.clock.sec)*1000000000+msg.clock.nanosec,
    wall_now(), identity.str());
  if (gate_.fault().empty()) {latest_ = msg;}
}

void ControlClockRelay::tick()
{
  const auto wall = wall_now();
  const auto selected = gate_.poll(wall, count_publishers(input_->get_topic_name()),
    count_publishers(output_->get_topic_name()));
  if (selected) {
    output_->publish(latest_);  // exact input object; no now(), offset, or interpolation
    trace({{"event", "publish"}, {"capture_ns", *selected},
      {"sec", latest_.clock.sec}, {"nanosec", latest_.clock.nanosec},
      {"received_wall_ns", gate_.receipt()}, {"published_wall_ns", wall},
      {"gid", gate_.gid()}, {"inputs", gate_.inputs()}, {"outputs", gate_.outputs()}});
    // Avoid alternate-tick50Hz alias from a minimum-spacing gate and timer jitter.
    timer_->reset();  // next deadline >=10ms after this completed publication
  }
  if (!gate_.fault().empty() && !fault_recorded_) {
    fault_recorded_ = true;
    trace({{"event", "fault"}, {"wall_ns", wall}, {"report", report()}});
    RCLCPP_ERROR(get_logger(), "control clock sticky fault: %s", gate_.fault().c_str());
  }
}

nlohmann::json ControlClockRelay::report() const
{
  return {{"mode", "relay100"}, {"fault", gate_.fault()}, {"closing", gate_.closing()},
    {"armed", gate_.armed()},
    {"last_source_receipt_ns", gate_.receipt()},
    {"last_source_capture_ns", static_cast<int64_t>(latest_.clock.sec)*1000000000+latest_.clock.nanosec},
    {"gid", gate_.gid()}, {"inputs", gate_.inputs()}, {"outputs", gate_.outputs()},
    {"source_topic", input_->get_topic_name()}, {"destination_topic", output_->get_topic_name()}};
}

void ControlClockRelay::trace(nlohmann::json row)
{
  try {sink_(row);} catch (...) {gate_.fail("trace_io_failure"); throw;}
}

void ControlClockRelay::finish()
{
  if (finished_) {return;}
  gate_.close(); timer_->cancel();
  trace({{"event", "closed"}, {"wall_ns", wall_now()}, {"report", report()}});
  finished_ = true;
}
}  // namespace integrated_robot_navigation_sensors
