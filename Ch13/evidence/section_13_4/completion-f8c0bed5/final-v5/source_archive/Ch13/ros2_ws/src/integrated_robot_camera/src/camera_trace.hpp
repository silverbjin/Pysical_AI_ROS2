// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <array>
#include <cstdint>
#include <map>
#include <string>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>

namespace integrated_robot_camera
{
inline constexpr std::array<const char *, 13> native_trace_keys{
  "submit_start", "submit_end", "acquire", "scene_start", "render_start", "render_end",
  "readback_end", "rgb_publish_start", "rgb_publish_end", "depth_publish_start",
  "depth_publish_end", "info_publish_start", "info_publish_end"};
struct NativeFrameTrace
{
  std::string source_frame;
  int64_t capture_ns{0};
  uint64_t local_epoch{0}, native_sequence{0};
  std::map<std::string, uint64_t> times_ns;
  std::string outcome{"PUBLISHED"};
  int64_t ros_now_ns{0};
};
struct TraceStats
{
  uint64_t attempted{0}, emitted{0}, dropped{0}, oversize{0}, errors{0};
};
// Construct before starting the worker; publish/stats are worker-owned until join.
// A successful publish means a DDS call, not delivery to any observer.
class CameraTrace
{
public:
  CameraTrace(const rclcpp::Node::SharedPtr & node, bool enabled, const std::string & run_id);
  ~CameraTrace();
  CameraTrace(const CameraTrace &) = delete;
  CameraTrace & operator=(const CameraTrace &) = delete;
  bool enabled() const noexcept {return enabled_;}
  bool publish(const NativeFrameTrace & frame) noexcept;
  void record_error() noexcept;
  const TraceStats & stats() const noexcept {return stats_;}
private:
  bool enabled_;
  std::string run_id_, producer_id_, boot_id_;
  TraceStats stats_;
  rclcpp::Logger logger_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
};
}  // namespace integrated_robot_camera
