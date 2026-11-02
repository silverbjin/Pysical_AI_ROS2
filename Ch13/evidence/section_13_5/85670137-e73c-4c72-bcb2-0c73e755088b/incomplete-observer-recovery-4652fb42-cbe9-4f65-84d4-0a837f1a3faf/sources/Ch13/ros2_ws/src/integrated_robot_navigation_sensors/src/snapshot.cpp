// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/snapshot.hpp"
#include <array>
#include <condition_variable>
#include <stdexcept>
#include <utility>

namespace integrated_robot_navigation_sensors
{
struct SnapshotState
{
  using Model = std::unique_ptr<mjModel, decltype(&mj_deleteModel)>;
  using Data = std::unique_ptr<mjData, decltype(&mj_deleteData)>;
  explicit SnapshotState(const mjModel * source)
  : model(source ? mj_copyModel(nullptr, source) : nullptr, mj_deleteModel),
    slots{Data(nullptr, mj_deleteData), Data(nullptr, mj_deleteData)}
  {
    if (mj_version() != mjVERSION_HEADER) {
      throw std::runtime_error("MuJoCo header/library version mismatch");
    }
    if (!model) {throw std::invalid_argument("snapshot requires a valid model");}
    for (auto & slot : slots) {
      slot.reset(mj_makeData(model.get()));
      if (!slot) {throw std::bad_alloc();}
    }
  }
  Model model;
  std::array<Data, 2> slots;
  std::mutex mutex;
  std::condition_variable changed;
  int leased{-1}, pending{-1};
  uint64_t sequence{0}, epoch{0};
  bool stopped{false};
};

SnapshotLease::SnapshotLease(std::shared_ptr<SnapshotState> state, int index,
  uint64_t sequence, uint64_t epoch)
: state_(std::move(state)), index_(index), sequence_(sequence), epoch_(epoch) {}
SnapshotLease::SnapshotLease(SnapshotLease && other) noexcept
: state_(std::move(other.state_)), index_(std::exchange(other.index_, -1)),
  sequence_(other.sequence_), epoch_(other.epoch_) {}
SnapshotLease & SnapshotLease::operator=(SnapshotLease && other) noexcept
{
  if (this != &other) {
    release(); state_ = std::move(other.state_);
    index_ = std::exchange(other.index_, -1);
    sequence_ = other.sequence_; epoch_ = other.epoch_;
  }
  return *this;
}
SnapshotLease::~SnapshotLease() {release();}
void SnapshotLease::release()
{
  if (!state_) {return;}
  {
    std::lock_guard<std::mutex> lock(state_->mutex);
    state_->leased = -1;
  }
  state_->changed.notify_all();
  state_.reset(); index_ = -1;
}
const mjData * SnapshotLease::data() const {return state_->slots[index_].get();}

SnapshotChannel::SnapshotChannel(const mjModel * model)
: state_(std::make_shared<SnapshotState>(model)) {}
const mjModel * SnapshotChannel::model() const {return state_->model.get();}
bool SnapshotChannel::submit(const mjModel * m, const mjData * d)
{
  std::lock_guard<std::mutex> lock(state_->mutex);
  if (state_->stopped) {return false;}
  if (!m || !d || m->nbuffer != model()->nbuffer || m->nq != model()->nq ||
    m->nv != model()->nv || m->nbody != model()->nbody || m->ngeom != model()->ngeom)
  {throw std::invalid_argument("snapshot model changed; restart required");}
  const int index = state_->pending >= 0 ? state_->pending : (state_->leased == 0 ? 1 : 0);
  // Full copy is essential: mjv_copyData does NOT retain constraint/contact forces.
  mj_copyData(state_->slots[index].get(), state_->model.get(), d);
  state_->pending = index;
  ++state_->sequence;
  state_->changed.notify_one();
  return true;
}
std::optional<SnapshotLease> SnapshotChannel::wait_take()
{
  std::unique_lock<std::mutex> lock(state_->mutex);
  state_->changed.wait(lock, [&] {
    return state_->stopped || (state_->pending >= 0 && state_->leased < 0);
  });
  if (state_->stopped) {return std::nullopt;}
  state_->leased = std::exchange(state_->pending, -1);
  return SnapshotLease(state_, state_->leased, state_->sequence, state_->epoch);
}
void SnapshotChannel::request_stop()
{
  std::lock_guard<std::mutex> lock(state_->mutex);
  if (!state_->stopped) {++state_->epoch;}
  state_->stopped = true; state_->pending = -1;
  state_->changed.notify_all();
}
bool SnapshotChannel::current(const SnapshotLease & lease) const
{
  std::lock_guard<std::mutex> lock(state_->mutex);
  return !state_->stopped && lease.epoch() == state_->epoch;
}

SensorWorker::SensorWorker(const mjModel * model, Callback callback)
: channel_(model), callback_(std::move(callback)), thread_([this] {run();}) {}
SensorWorker::~SensorWorker() {stop();}
void SensorWorker::run()
{
  try {
    while (auto lease = channel_.wait_take()) {callback_(*lease, *this);}
  } catch (...) {
    failed_ = true;
    request_stop();
  }
}
void SensorWorker::request_stop()
{
  std::lock_guard<std::mutex> lock(egress_mutex_);
  channel_.request_stop();
}
void SensorWorker::stop()
{
  std::lock_guard<std::mutex> lock(join_mutex_);
  request_stop();
  if (thread_.joinable()) {thread_.join();}
}
bool SensorWorker::publish_if_current(const SnapshotLease & lease,
  const std::function<void()> & publish)
{
  std::lock_guard<std::mutex> lock(egress_mutex_);
  if (!channel_.current(lease)) {return false;}
  publish();
  return true;
}
}  // namespace integrated_robot_navigation_sensors
