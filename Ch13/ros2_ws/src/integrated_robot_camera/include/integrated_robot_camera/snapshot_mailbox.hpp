// SPDX-License-Identifier: Apache-2.0
#ifndef INTEGRATED_ROBOT_CAMERA__SNAPSHOT_MAILBOX_HPP_
#define INTEGRATED_ROBOT_CAMERA__SNAPSHOT_MAILBOX_HPP_

#include <mujoco/mujoco.h>

#include <array>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <mutex>
#include <optional>
#include <vector>

namespace integrated_robot_camera
{
// Explicit Linux CLOCK_MONOTONIC, never ROS/simulation time. Zero means failure.
uint64_t monotonic_nanoseconds() noexcept;
struct FrameTiming
{
  uint64_t submit_start_ns{0};
  uint64_t submit_end_ns{0};
  uint64_t acquire_ns{0};
};
struct ClockObservation
{
  uint64_t epoch;
  bool rollback;
};

// The model outlives this mailbox. Stop + join all callers and destroy every
// lease before destroying the mailbox. No GL/ROS operation runs under its lock.
class SnapshotMailbox
{
  struct Slot
  {
    std::unique_ptr<mjData, decltype(&mj_deleteData)> data{nullptr, mj_deleteData};
    double stamp{0.};
    uint64_t sequence{0};
    uint64_t epoch{0};
    FrameTiming timing;
    std::vector<size_t> cameras;
    std::vector<size_t> retained_cameras;
  };

public:
  class RenderLease
  {
  public:
    ~RenderLease();
    RenderLease(RenderLease && other) noexcept;
    RenderLease & operator=(RenderLease && other) noexcept;
    RenderLease(const RenderLease &) = delete;
    RenderLease & operator=(const RenderLease &) = delete;
    const mjData * data() const noexcept {return slot_->data.get();}
    double stamp_seconds() const noexcept {return slot_->stamp;}
    uint64_t sequence() const noexcept {return slot_->sequence;}
    uint64_t epoch() const noexcept {return slot_->epoch;}
    const FrameTiming & timing() const noexcept {return slot_->timing;}
    const std::vector<size_t> & camera_indices() const noexcept {return slot_->cameras;}

  private:
    friend class SnapshotMailbox;
    RenderLease(SnapshotMailbox * owner, const Slot * slot) noexcept;
    void release() noexcept;
    SnapshotMailbox * owner_;
    const Slot * slot_;
  };

  explicit SnapshotMailbox(const mjModel * model, size_t camera_count, bool trace_enabled = false);
  SnapshotMailbox(const SnapshotMailbox &) = delete;
  SnapshotMailbox & operator=(const SnapshotMailbox &) = delete;
  SnapshotMailbox(SnapshotMailbox &&) = delete;
  SnapshotMailbox & operator=(SnapshotMailbox &&) = delete;

  ClockObservation observe_time(double sim_time);
  bool submit(const mjModel * model, const mjData * data,
    const std::vector<size_t> & cameras, uint64_t observed_epoch);
  // One-shot requests survive pending overwrites, but never the acquisition of
  // that pending frame. With no retained requests, selection is exactly latest-only.
  bool submit(const mjModel * model, const mjData * data,
    const std::vector<size_t> & cameras, uint64_t observed_epoch,
    const std::vector<size_t> & retain_until_acquired);
  std::optional<RenderLease> wait_take();
  bool is_current(uint64_t epoch) const;
  void reset_epoch();
  void request_stop();

private:
  void release_render() noexcept;
  const mjModel * model_;
  const size_t camera_count_;
  const bool trace_enabled_;
  std::array<Slot, 2> slots_;
  size_t pending_index_{0};
  size_t render_index_{1};
  mutable std::mutex mutex_;
  std::condition_variable ready_;
  bool pending_{false};
  bool render_in_use_{false};
  bool consumer_waiting_{false};
  bool stopped_{false};
  std::optional<double> last_time_;
  uint64_t epoch_{0};
  uint64_t sequence_{0};
};
}  // namespace integrated_robot_camera
#endif  // INTEGRATED_ROBOT_CAMERA__SNAPSHOT_MAILBOX_HPP_
