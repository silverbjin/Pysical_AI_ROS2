// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <rclcpp/rclcpp.hpp>
#include <tf2_msgs/msg/tf_message.hpp>
#include <nlohmann/json.hpp>
#include <functional>
#include <set>
#include <tuple>

namespace integrated_robot_navigation_sensors
{
// Read-only authority observer. It never publishes TF, state, or motor commands.
class TfProvenanceObserver : public rclcpp::Node
{
public:
  explicit TfProvenanceObserver(std::function<void(const nlohmann::json &)> sink);
private:
  void receive(const tf2_msgs::msg::TFMessage &, const rclcpp::MessageInfo &,
    const std::string & topic);
  std::function<void(const nlohmann::json &)> sink_;
  std::set<std::tuple<std::string, std::string, std::string, std::string>> seen_;
  rclcpp::Subscription<tf2_msgs::msg::TFMessage>::SharedPtr dynamic_, fixed_;
};
}  // namespace integrated_robot_navigation_sensors
