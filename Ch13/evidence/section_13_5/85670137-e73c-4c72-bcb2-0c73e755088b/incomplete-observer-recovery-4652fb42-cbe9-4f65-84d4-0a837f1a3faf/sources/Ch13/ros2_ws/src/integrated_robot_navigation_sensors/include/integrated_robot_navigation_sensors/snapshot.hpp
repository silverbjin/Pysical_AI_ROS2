// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <mujoco/mujoco.h>
#include <atomic>
#include <cstdint>
#include <functional>
#include <memory>
#include <mutex>
#include <optional>
#include <thread>

namespace integrated_robot_navigation_sensors
{
struct SnapshotState;
class SnapshotLease
{
public:
  SnapshotLease(const SnapshotLease &) = delete;
  SnapshotLease & operator=(const SnapshotLease &) = delete;
  SnapshotLease(SnapshotLease &&) noexcept;
  SnapshotLease & operator=(SnapshotLease &&) noexcept;
  ~SnapshotLease();
  const mjData * data() const;
  uint64_t sequence() const {return sequence_;}
  uint64_t epoch() const {return epoch_;}
private:
  friend class SnapshotChannel;
  SnapshotLease(std::shared_ptr<SnapshotState>, int, uint64_t, uint64_t);
  void release();
  std::shared_ptr<SnapshotState> state_;
  int index_{-1};
  uint64_t sequence_{0}, epoch_{0};
};

// One consumer, latest pending frame. Leases retain BOTH model and full data.
class SnapshotChannel
{
public:
  explicit SnapshotChannel(const mjModel *);
  bool submit(const mjModel *, const mjData *);
  std::optional<SnapshotLease> wait_take();
  const mjModel * model() const;
  void request_stop();
  bool current(const SnapshotLease &) const;
private:
  std::shared_ptr<SnapshotState> state_;
};

class SensorWorker
{
public:
  using Callback = std::function<void(const SnapshotLease &, SensorWorker &)>;
  SensorWorker(const mjModel *, Callback);
  ~SensorWorker();
  bool submit(const mjModel * m, const mjData * d) {return channel_.submit(m, d);}
  const mjModel * model() const {return channel_.model();}
  void request_stop();
  void stop();
  bool publish_if_current(const SnapshotLease &, const std::function<void()> &);
  bool failed() const {return failed_.load();}
private:
  void run();
  SnapshotChannel channel_;
  Callback callback_;
  std::mutex egress_mutex_, join_mutex_;
  std::atomic<bool> failed_{false};
  std::thread thread_;
};
}  // namespace integrated_robot_navigation_sensors
