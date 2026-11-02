// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <array>
#include <atomic>
#include <cmath>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <mutex>
#include <thread>
#include <stdexcept>
#include <utility>

namespace integrated_robot_navigation_sensors
{
struct AppliedReferenceRow
{
  int64_t stamp_ns{0};
  std::array<double,64> values{};
};

// Physics copies bounded numeric data without waiting. ROS allocation and
// publication belong to this worker, which never writes any simulator data.
class AppliedReferenceWorker
{
public:
  using Publish=std::function<void(const AppliedReferenceRow &)>;
  AppliedReferenceWorker(size_t count,Publish publish)
  : count_(count),publish_(std::move(publish))
  {
    if(count==0 || count>64) {throw std::invalid_argument("applied reference dimensions");}
    thread_=std::thread([this] {run();});
  }
  ~AppliedReferenceWorker() {stop();}
  void submit(const AppliedReferenceRow & row)
  {
    if(!accepting_.load()) {return;}
    std::unique_lock<std::mutex> lock(mutex_,std::try_to_lock);
    if(!lock.owns_lock()) {++busy_;return;}
    if(!accepting_.load()) {return;}
    bool valid=row.stamp_ns>=0 && row.stamp_ns>=last_observed_;
    for(size_t i=0;i<count_;++i) {valid=valid && std::isfinite(row.values[i]);}
    if(!valid) {failed_=true;accepting_=false;wake_.notify_one();return;}
    last_observed_=row.stamp_ns;
    bool changed=!seen_;
    for(size_t i=0;i<count_;++i) {changed=changed || row.values[i]!=latest_.values[i];}
    if(!changed) {return;} // Never renew an unchanged application timestamp.
    if(pending_) {++overwritten_;}
    latest_=row;seen_=pending_=true;++submitted_;
    lock.unlock();wake_.notify_one();
  }
  void request_stop() {accepting_=false;wake_.notify_one();}
  void fail() {failed_=true;request_stop();}
  void stop()
  {
    request_stop();
    if(thread_.joinable()) {thread_.join();}
    joined_=true;
  }
  bool failed() const {return failed_.load();}
  bool joined() const {return joined_.load();}
  uint64_t submitted() const {return submitted_.load();}
  uint64_t published() const {return published_.load();}
  uint64_t dropped_busy() const {return busy_.load();}
  uint64_t overwritten() const {return overwritten_.load();}
private:
  void run()
  {
    while(true) {
      AppliedReferenceRow row;
      {
        std::unique_lock<std::mutex> lock(mutex_);
        // request_stop() cannot acquire a physics-thread mutex. A bounded wait
        // also covers a notification racing the predicate/wait boundary.
        wake_.wait_for(lock,std::chrono::milliseconds(10),
          [this] {return pending_ || !accepting_.load();});
        if(!pending_) {if(!accepting_.load()) {return;} else {continue;}}
        row=latest_;pending_=false;
      }
      try {publish_(row);++published_;}
      catch(...) {failed_=true;request_stop();return;}
    }
  }
  size_t count_;
  Publish publish_;
  std::thread thread_;
  std::mutex mutex_;
  std::condition_variable wake_;
  AppliedReferenceRow latest_;
  int64_t last_observed_{-1};
  bool seen_{false},pending_{false};
  std::atomic<bool> accepting_{true},failed_{false},joined_{false};
  std::atomic<uint64_t> submitted_{0},published_{0},busy_{0},overwritten_{0};
};
} // namespace integrated_robot_navigation_sensors
