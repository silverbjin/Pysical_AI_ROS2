// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_camera/snapshot_mailbox.hpp"

#include <cmath>
#include <algorithm>
#include <new>
#include <stdexcept>
#include <utility>
#include <time.h>

namespace integrated_robot_camera
{
namespace
{
void validate_time(double time)
{
  if (!std::isfinite(time) || time < 0.) {
    throw std::invalid_argument("snapshot time must be finite and nonnegative");
  }
}
}  // namespace

uint64_t monotonic_nanoseconds() noexcept
{
  timespec now{};
  if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {return 0;}
  return static_cast<uint64_t>(now.tv_sec) * 1000000000ULL + now.tv_nsec;
}

SnapshotMailbox::SnapshotMailbox(const mjModel * model, size_t camera_count, bool trace_enabled)
: model_(model), camera_count_(camera_count), trace_enabled_(trace_enabled)
{
  if (!model || camera_count > static_cast<size_t>(model->ncam)) {
    throw std::invalid_argument("invalid snapshot model or camera count");
  }
  for (auto & slot : slots_) {
    slot.data.reset(mj_makeData(model));
    if (!slot.data) {
      throw std::bad_alloc();
    }
    slot.cameras.reserve(camera_count);
    slot.retained_cameras.reserve(camera_count);
  }
}

ClockObservation SnapshotMailbox::observe_time(double sim_time)
{
  validate_time(sim_time);
  std::lock_guard<std::mutex> lock(mutex_);
  const bool rollback = last_time_ && sim_time < *last_time_;
  if (rollback) {
    ++epoch_;
    pending_ = false;
  }
  last_time_ = sim_time;
  return {epoch_, rollback};
}

bool SnapshotMailbox::submit(const mjModel * model, const mjData * data,
  const std::vector<size_t> & cameras, uint64_t observed_epoch)
{
  return submit(model, data, cameras, observed_epoch, {});
}

bool SnapshotMailbox::submit(const mjModel * model, const mjData * data,
  const std::vector<size_t> & cameras, uint64_t observed_epoch,
  const std::vector<size_t> & retain_until_acquired)
{
  const auto submit_start = trace_enabled_ ? monotonic_nanoseconds() : 0;
  if (model != model_ || !data) {
    throw std::invalid_argument("snapshot model mismatch or null data");
  }
  validate_time(data->time);
  for (size_t i = 0; i < cameras.size(); ++i) {
    if (cameras[i] >= camera_count_) {
      throw std::invalid_argument("snapshot camera index out of range");
    }
    for (size_t j = 0; j < i; ++j) {
      if (cameras[i] == cameras[j]) {
        throw std::invalid_argument("duplicate snapshot camera index");
      }
    }
  }
  for (size_t i = 0; i < retain_until_acquired.size(); ++i) {
    const auto id = retain_until_acquired[i];
    if (std::find(cameras.begin(), cameras.end(), id) == cameras.end() ||
      std::find(retain_until_acquired.begin(), retain_until_acquired.begin() + i, id) !=
      retain_until_acquired.begin() + i)
    {
      throw std::invalid_argument("retained cameras must be unique selected cameras");
    }
  }
  {
    std::lock_guard<std::mutex> lock(mutex_);
    if (stopped_ || observed_epoch != epoch_) {
      return false;
    }
    auto & slot = slots_[pending_index_];
    if (!pending_) {slot.retained_cameras.clear();}
    for (const auto id : retain_until_acquired) {
      if (std::find(slot.retained_cameras.begin(), slot.retained_cameras.end(), id) ==
        slot.retained_cameras.end()) {slot.retained_cameras.push_back(id);}
    }
    // Visualization state only, matching the native upstream camera contract.
    // This never writes slots_[render_index_] while a consumer holds its lease.
    mjv_copyData(slot.data.get(), model_, data);
    slot.stamp = data->time;
    slot.epoch = epoch_;
    slot.sequence = ++sequence_;
    slot.cameras.assign(cameras.begin(), cameras.end());
    for (const auto id : slot.retained_cameras) {
      if (std::find(slot.cameras.begin(), slot.cameras.end(), id) == slot.cameras.end()) {
        slot.cameras.push_back(id);
      }
    }
    slot.timing = {submit_start, trace_enabled_ ? monotonic_nanoseconds() : 0, 0};
    pending_ = true;
  }
  ready_.notify_one();
  return true;
}

std::optional<SnapshotMailbox::RenderLease> SnapshotMailbox::wait_take()
{
  std::unique_lock<std::mutex> lock(mutex_);
  if (render_in_use_ || consumer_waiting_) {
    throw std::logic_error("only one renderer and one outstanding lease are allowed");
  }
  consumer_waiting_ = true;
  ready_.wait(lock, [this] {return stopped_ || pending_;});
  consumer_waiting_ = false;
  if (stopped_) {
    return std::nullopt;
  }
  std::swap(pending_index_, render_index_);
  pending_ = false;
  render_in_use_ = true;
  slots_[render_index_].timing.acquire_ns = trace_enabled_ ? monotonic_nanoseconds() : 0;
  return RenderLease(this, &slots_[render_index_]);
}

bool SnapshotMailbox::is_current(uint64_t epoch) const
{
  std::lock_guard<std::mutex> lock(mutex_);
  return !stopped_ && epoch == epoch_;
}

void SnapshotMailbox::reset_epoch()
{
  std::lock_guard<std::mutex> lock(mutex_);
  ++epoch_;
  pending_ = false;
  last_time_.reset();
}

void SnapshotMailbox::request_stop()
{
  {
    std::lock_guard<std::mutex> lock(mutex_);
    stopped_ = true;
    pending_ = false;
  }
  ready_.notify_all();
}

void SnapshotMailbox::release_render() noexcept
{
  std::lock_guard<std::mutex> lock(mutex_);
  render_in_use_ = false;
}

SnapshotMailbox::RenderLease::RenderLease(SnapshotMailbox * owner, const Slot * slot) noexcept
: owner_(owner), slot_(slot) {}

SnapshotMailbox::RenderLease::~RenderLease() {release();}

void SnapshotMailbox::RenderLease::release() noexcept
{
  if (owner_) {
    owner_->release_render();
    owner_ = nullptr;
    slot_ = nullptr;
  }
}

SnapshotMailbox::RenderLease::RenderLease(RenderLease && other) noexcept
: owner_(std::exchange(other.owner_, nullptr)), slot_(std::exchange(other.slot_, nullptr)) {}

SnapshotMailbox::RenderLease & SnapshotMailbox::RenderLease::operator=(RenderLease && other) noexcept
{
  if (this != &other) {
    release();
    owner_ = std::exchange(other.owner_, nullptr);
    slot_ = std::exchange(other.slot_, nullptr);
  }
  return *this;
}
}  // namespace integrated_robot_camera
