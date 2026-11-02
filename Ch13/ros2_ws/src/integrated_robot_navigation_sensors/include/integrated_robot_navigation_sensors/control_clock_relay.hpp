// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "integrated_robot_navigation_sensors/control_clock_gate.hpp"
#include <rclcpp/rclcpp.hpp>
#include <rosgraph_msgs/msg/clock.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <nlohmann/json.hpp>
#include <functional>
#include <deque>

namespace integrated_robot_navigation_sensors
{
// All resources belong to the single-threaded executor. No physics, command,
// TF or sensor subscription; the node itself never uses simulated time.
class ControlClockRelay : public rclcpp::Node
{
public:
  explicit ControlClockRelay(std::function<void(const nlohmann::json &)> sink,
    const rclcpp::NodeOptions & options = rclcpp::NodeOptions());
  nlohmann::json report() const;
  void finish();
private:
  void receive(const rosgraph_msgs::msg::Clock &, const rclcpp::MessageInfo &);
  void tick();
  void trace(nlohmann::json row);
  static int64_t wall_now();
  static int64_t raw_now();
  struct InputReceipt {
    uint64_t sequence;
    int64_t capture, wall, system, source_system, rmw_system, raw_before, raw_after;
    std::string verdict;
  };
  struct PublicationSpan {
    uint64_t sequence;
    int64_t poll_wall, publish_start, publish_finish, trace_start, trace_finish;
  };
  void retain(InputReceipt receipt);
  nlohmann::json input_transport() const;
  nlohmann::json publication_work() const;
  ControlClockGate gate_;
  std::function<void(const nlohmann::json &)> sink_;
  rosgraph_msgs::msg::Clock latest_;
  rclcpp::Subscription<rosgraph_msgs::msg::Clock>::SharedPtr input_;
  rclcpp::Publisher<rosgraph_msgs::msg::Clock>::SharedPtr output_;
  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr report_, stop_, arm_;
  bool fault_recorded_{false}, finished_{false};
  uint64_t input_receipts_{0};
  std::deque<InputReceipt> input_transport_;
  std::deque<PublicationSpan> publication_work_;
};
}  // namespace integrated_robot_navigation_sensors
