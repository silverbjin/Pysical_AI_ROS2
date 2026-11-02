// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/tf_provenance.hpp"
#include <algorithm>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace integrated_robot_navigation_sensors
{
TfProvenanceObserver::TfProvenanceObserver(std::function<void(const nlohmann::json &)> sink)
: Node("navigation_tf_provenance"), sink_(std::move(sink))
{
  if (!sink_) {throw std::invalid_argument("TF provenance sink required");}
  dynamic_ = create_subscription<tf2_msgs::msg::TFMessage>("/tf",
    rclcpp::QoS(100).best_effort(),
    [this](tf2_msgs::msg::TFMessage::ConstSharedPtr msg, const rclcpp::MessageInfo & info) {
      receive(*msg, info, "/tf");
    });
  fixed_ = create_subscription<tf2_msgs::msg::TFMessage>("/tf_static",
    rclcpp::QoS(100).reliable().transient_local(),
    [this](tf2_msgs::msg::TFMessage::ConstSharedPtr msg, const rclcpp::MessageInfo & info) {
      receive(*msg, info, "/tf_static");
    });
}

void TfProvenanceObserver::receive(const tf2_msgs::msg::TFMessage & msg,
  const rclcpp::MessageInfo & message_info, const std::string & topic)
{
  const auto & info = message_info.get_rmw_message_info();
  const auto & bytes = info.publisher_gid.data;
  if (std::all_of(std::begin(bytes), std::end(bytes), [](auto byte) {return byte == 0;})) {
    throw std::runtime_error("native TF publisher GID unavailable; no graph substitution");
  }
  std::ostringstream identity;
  for (const auto byte : bytes) {
    identity << std::hex << std::setfill('0') << std::setw(2) << static_cast<unsigned>(byte);
  }
  const auto gid = identity.str();
  for (const auto & transform : msg.transforms) {
    const auto & header = transform.header;
    const auto key = std::make_tuple(topic, header.frame_id, transform.child_frame_id, gid);
    if (seen_.find(key) != seen_.end()) {continue;}
    // Deduplicate only identical authority tuples, never a replacement owner or
    // changed parent/topic. This bounds disk I/O without fabricating identity.
    sink_(nlohmann::json{{"topic", topic}, {"parent", header.frame_id},
      {"child", transform.child_frame_id}, {"gid", gid},
      {"stamp_ns", static_cast<int64_t>(header.stamp.sec)*1000000000LL+header.stamp.nanosec},
      {"source_timestamp", info.source_timestamp},
      {"received_wall_ns", std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count()}});
    seen_.insert(key);  // sink failures cannot be silently counted as recorded
  }
}
}  // namespace integrated_robot_navigation_sensors
