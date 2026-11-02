// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <mutex>
#include <vector>
#include <nlohmann/json.hpp>

namespace integrated_robot_navigation_sensors
{
// Diagnostic only. Producers copy fixed numeric rows; they never allocate,
// serialize, write files, wait on an exporter, or modify a motor reference.
struct CommandTraceRow
{
  uint64_t sequence{0};
  int64_t snapshot_ros_ns{0}, steady_ns{0};
  std::array<double, 64> ctrl{}, joint_velocity{};
  std::array<double, 3> body_angular_velocity{};
};

class CommandTraceLane
{
public:
  explicit CommandTraceLane(size_t capacity) : slots_(capacity) {}
  void record(CommandTraceRow row, const std::atomic<bool> & accepting)
  {
    if (!accepting.load(std::memory_order_acquire)) {return;}
    std::unique_lock<std::mutex> lock(mutex_, std::try_to_lock);
    if (!lock.owns_lock()) {++dropped_busy_; return;}
    if (!accepting.load(std::memory_order_acquire)) {return;}
    row.sequence = ++total_;
    slots_[(total_-1)%slots_.size()] = row;
  }
  nlohmann::json export_frozen(size_t dimensions, size_t last_rows)
  {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto retained = std::min<uint64_t>(total_, slots_.size());
    const auto exported = std::min<uint64_t>(retained, last_rows);
    auto rows = nlohmann::json::array();
    for (auto sequence = total_-exported+1; sequence <= total_; ++sequence) {
      const auto & row = slots_[(sequence-1)%slots_.size()];
      rows.push_back({{"sequence", row.sequence}, {"snapshot_ros_ns", row.snapshot_ros_ns},
        {"steady_ns", row.steady_ns},
        {"ctrl", std::vector<double>(row.ctrl.begin(), row.ctrl.begin()+dimensions)},
        {"joint_velocity", std::vector<double>(row.joint_velocity.begin(), row.joint_velocity.begin()+dimensions)},
        {"body_angular_velocity", row.body_angular_velocity}});
    }
    return {{"capacity", slots_.size()}, {"total", total_}, {"overwritten", total_-retained},
      {"omitted_from_export", retained-exported}, {"dropped_busy", dropped_busy_.load()}, {"rows", rows}};
  }
private:
  std::mutex mutex_;
  std::vector<CommandTraceRow> slots_;
  uint64_t total_{0};
  std::atomic<uint64_t> dropped_busy_{0};
};

struct NativeCommandTrace
{
  std::atomic<bool> accepting{true};
  std::atomic<uint64_t> invalid_time{0};
  CommandTraceLane cm_write{4096}, pre_step{16384};
  void stop() {accepting.store(false, std::memory_order_release);}
};
}  // namespace integrated_robot_navigation_sensors
