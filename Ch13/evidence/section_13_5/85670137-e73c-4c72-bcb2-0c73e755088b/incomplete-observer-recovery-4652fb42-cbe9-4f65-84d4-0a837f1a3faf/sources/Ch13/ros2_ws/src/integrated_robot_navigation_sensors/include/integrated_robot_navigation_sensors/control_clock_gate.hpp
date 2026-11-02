// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <cstdint>
#include <optional>
#include <string>

namespace integrated_robot_navigation_sensors
{
// Single-owner state machine: all calls serialized by the node's executor.
// No wall->ROS conversion, interpolation, recovery or mutable rate parameter.
class ControlClockGate
{
public:
  void receive(int64_t capture, int64_t wall, const std::string & gid)
  {
    if (!check_wall(wall) || closing_ || !fault_.empty()) {return;}
    if (capture < 0) {fail("invalid_stamp"); return;}
    if (gid.empty()) {fail("invalid_gid"); return;}
    if (!gid_.empty() && gid != gid_) {fail("source_changed"); return;}
    if (latest_ && capture < *latest_) {fail("source_rollback"); return;}
    gid_ = gid;
    ++inputs_;
    if (!latest_ || capture > *latest_) {
      latest_ = capture;
      receipt_ = wall;
      if (capture > 0) {progress_ = wall;}
    }
  }

  std::optional<int64_t> poll(int64_t wall, size_t sources, size_t destinations)
  {
    if (!check_wall(wall) || closing_ || !fault_.empty()) {return {};}
    if (sources > 1 || (!gid_.empty() && sources != 1)) {fail("source_count"); return {};}
    if (destinations != 1) {fail("destination_count"); return {};}
    if (!latest_ || latest_ == published_) {return {};}
    if (wall - receipt_ > 200000000) {return {};}
    if (last_publish_ && wall - *last_publish_ < 10000000) {return {};}
    published_ = latest_;
    last_publish_ = wall;
    ++outputs_;
    return published_;
  }

  void fail(const std::string & reason) {if (fault_.empty()) {fault_ = reason;}}
  bool arm(int64_t wall)
  {
    if (!check_wall(wall) || closing_) {return false;}
    if (!progress_ || wall - *progress_ > 200000000) {
      fail("arming_requires_fresh_positive_clock"); return false;
    }
    armed_ = true;  // never renew the original progress/receipt lease
    return true;
  }
  bool armed() const {return armed_;}
  void close() {closing_ = true;}
  bool closing() const {return closing_;}
  const std::string & fault() const {return fault_;}
  const std::string & gid() const {return gid_;}
  uint64_t inputs() const {return inputs_;}
  uint64_t outputs() const {return outputs_;}
  int64_t receipt() const {return receipt_;}

private:
  bool check_wall(int64_t wall)
  {
    if (wall < 0 || (last_wall_ && wall < *last_wall_)) {fail("wall_rollback"); return false;}
    last_wall_ = wall;
    if (armed_ && progress_ && wall - *progress_ > 200000000) {fail("source_stalled");}
    return fault_.empty();
  }
  std::optional<int64_t> latest_, published_, last_publish_, progress_, last_wall_;
  std::string gid_, fault_;
  int64_t receipt_{0};
  uint64_t inputs_{0}, outputs_{0};
  bool closing_{false}, armed_{false};
};
}  // namespace integrated_robot_navigation_sensors
