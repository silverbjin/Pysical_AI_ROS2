// SPDX-License-Identifier: Apache-2.0
#include "camera_trace.hpp"
#include <fstream>
#include <iomanip>
#include <random>
#include <sstream>
#include <stdexcept>
#include <sys/syscall.h>
#include <unistd.h>

namespace integrated_robot_camera
{
namespace
{
constexpr size_t max_bytes = 4096, max_records = 20000;
bool uuid(const std::string & value)
{
  if (value.size() != 36) {return false;}
  for (size_t i = 0; i < value.size(); ++i) {
    if (i == 8 || i == 13 || i == 18 || i == 23) {
      if (value[i] != '-') {return false;}
    } else if (!((value[i] >= '0' && value[i] <= '9') ||
      (value[i] >= 'a' && value[i] <= 'f'))) {return false;}
  }
  return true;
}
std::string producer_uuid()
{
  std::random_device random;
  std::array<unsigned char, 16> bytes{};
  for (auto & byte : bytes) {byte = static_cast<unsigned char>(random());}
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  std::ostringstream output;
  output << std::hex << std::setfill('0');
  for (size_t i = 0; i < bytes.size(); ++i) {
    if (i == 4 || i == 6 || i == 8 || i == 10) {output << '-';}
    output << std::setw(2) << static_cast<unsigned>(bytes[i]);
  }
  return output.str();
}
// Reject malformed UTF-8 rather than publishing JSON that decoders cannot read.
bool utf8(const std::string & value)
{
  for (size_t i = 0; i < value.size();) {
    const auto byte = static_cast<unsigned char>(value[i++]);
    if (byte < 128) {continue;}
    unsigned count = 0, code = 0, minimum = 0;
    if (byte >= 0xc2 && byte <= 0xdf) {count = 1; code = byte & 31; minimum = 128;}
    else if (byte >= 0xe0 && byte <= 0xef) {count = 2; code = byte & 15; minimum = 2048;}
    else if (byte >= 0xf0 && byte <= 0xf4) {count = 3; code = byte & 7; minimum = 65536;}
    else {return false;}
    if (i + count > value.size()) {return false;}
    while (count--) {
      const auto next = static_cast<unsigned char>(value[i++]);
      if ((next & 0xc0) != 0x80) {return false;}
      code = (code << 6) | (next & 63);
    }
    if (code < minimum || code > 0x10ffff || (code >= 0xd800 && code <= 0xdfff)) {return false;}
  }
  return true;
}
std::string quote(const std::string & value)
{
  std::ostringstream output;
  output << '"';
  for (unsigned char byte : value) {
    if (byte == '"' || byte == '\\') {output << '\\' << byte;}
    else if (byte == '\n') {output << "\\n";}
    else if (byte == '\r') {output << "\\r";}
    else if (byte == '\t') {output << "\\t";}
    else if (byte < 32) {
      output << "\\u" << std::hex << std::setfill('0') << std::setw(4) << unsigned(byte);
    } else {output << byte;}
  }
  output << '"';
  return output.str();
}
}  // namespace

CameraTrace::CameraTrace(const rclcpp::Node::SharedPtr & node, bool enabled,
  const std::string & run_id)
: enabled_(enabled), logger_(node->get_logger())
{
  if (!enabled_) {return;}
  if (!uuid(run_id)) {throw std::invalid_argument("trace_run_id must be a canonical UUID");}
  run_id_ = run_id;
  producer_id_ = producer_uuid();
  std::ifstream boot("/proc/sys/kernel/random/boot_id");
  std::getline(boot, boot_id_);
  if (!uuid(boot_id_)) {throw std::runtime_error("trace cannot identify Linux boot clock");}
  publisher_ = node->create_publisher<std_msgs::msg::String>("/vision/camera_trace",
    rclcpp::QoS(rclcpp::KeepLast(32)).best_effort().durability_volatile());
}

CameraTrace::~CameraTrace()
{
  if (!enabled_) {return;}
  RCLCPP_INFO(logger_,
    "camera_trace_totals run_id=%s producer_id=%s attempted=%lu emitted=%lu drop=%lu oversize=%lu errors=%lu",
    run_id_.c_str(), producer_id_.c_str(), stats_.attempted, stats_.emitted,
    stats_.dropped, stats_.oversize, stats_.errors);
}

void CameraTrace::record_error() noexcept
{
  if (enabled_) {++stats_.attempted; ++stats_.dropped; ++stats_.errors;}
}

bool CameraTrace::publish(const NativeFrameTrace & frame) noexcept
{
  if (!enabled_) {return false;}
  const auto sequence = ++stats_.attempted;
  if (sequence > max_records) {++stats_.dropped; return false;}
  try {
    if (frame.source_frame.size() > max_bytes || frame.outcome.size() > max_bytes) {
      ++stats_.oversize; ++stats_.dropped; return false;
    }
    if (frame.source_frame.empty() || frame.capture_ns < 0 || frame.ros_now_ns < 0 ||
      frame.outcome.empty() || !utf8(frame.source_frame) || !utf8(frame.outcome) ||
      frame.times_ns.size() != native_trace_keys.size())
    {throw std::invalid_argument("malformed native trace");}
    uint64_t previous = 0;
    for (const auto key : native_trace_keys) {
      const auto now = frame.times_ns.at(key);
      if (!now || now < previous) {throw std::invalid_argument("nonmonotonic native trace");}
      previous = now;
    }
    std::ostringstream output;
    output << "{\"schema_version\":1,\"run_id\":" << quote(run_id_)
      << ",\"producer_id\":" << quote(producer_id_) << ",\"pid\":" << getpid()
      << ",\"tid\":" << syscall(SYS_gettid) << ",\"clock_id\":\"linux/CLOCK_MONOTONIC\""
      << ",\"boot_id\":" << quote(boot_id_) << ",\"stage\":\"camera\",\"event_sequence\":" << sequence
      << ",\"source_frame\":" << quote(frame.source_frame) << ",\"capture_ns\":" << frame.capture_ns
      << ",\"local_epoch\":" << frame.local_epoch << ",\"native_sequence\":" << frame.native_sequence
      << ",\"ros_now_ns\":" << frame.ros_now_ns << ",\"outcome\":" << quote(frame.outcome)
      << ",\"times_ns\":{";
    bool first = true;
    for (const auto & entry : frame.times_ns) {
      if (!first) {output << ',';} first = false;
      output << quote(entry.first) << ':' << entry.second;
    }
    output << "}}";
    std_msgs::msg::String message;
    message.data = output.str();
    if (message.data.size() > max_bytes) {++stats_.oversize; ++stats_.dropped; return false;}
    publisher_->publish(message);
    ++stats_.emitted;
    return true;
  } catch (...) {++stats_.errors; ++stats_.dropped; return false;}
}
}  // namespace integrated_robot_camera
