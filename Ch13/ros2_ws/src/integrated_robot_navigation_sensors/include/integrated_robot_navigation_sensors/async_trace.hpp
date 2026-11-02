// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <nlohmann/json.hpp>
#include <algorithm>
#include <condition_variable>
#include <deque>
#include <functional>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>

namespace integrated_robot_navigation_sensors
{
// One serialized producer, one write-only worker. No ROS/clock/model access.
// Limits include the in-flight record. Overflow/write error is terminal;
// accepted records are never coalesced or retried. Finish blocks new records,
// drains accepted work, and joins BEFORE the caller can close its descriptor.
class AsyncTrace
{
public:
  explicit AsyncTrace(std::function<void(const std::string &)> sink,
    size_t capacity=128,size_t maximum_bytes=4*1024*1024)
  : sink_(std::move(sink)),capacity_(capacity),maximum_bytes_(maximum_bytes)
  {
    if(!sink_ || !capacity_ || !maximum_bytes_){throw std::invalid_argument("trace limits/sink");}
    worker_=std::thread([this]{run();});
  }
  AsyncTrace(const AsyncTrace &)=delete;
  AsyncTrace & operator=(const AsyncTrace &)=delete;
  ~AsyncTrace(){try{finish();}catch(...){/* explicit finish reports failure to main */}}

  void submit(const nlohmann::json & row)
  {
    auto line=row.dump()+"\n";  // bounded-schema encoding only; NEVER file IO
    std::lock_guard<std::mutex> lock(mutex_);
    if(!error_.empty()){throw std::runtime_error(error_);}
    if(closed_){throw std::runtime_error("trace_closed");}
    if(accepted_-written_>=capacity_){fail_locked("trace_queue_capacity");throw std::runtime_error(error_);}
    if(line.size()>maximum_bytes_-pending_bytes_){fail_locked("trace_queue_bytes");throw std::runtime_error(error_);}
    queue_.push_back(std::move(line));pending_bytes_+=queue_.back().size();++accepted_;
    peak_records_=std::max(peak_records_,accepted_-written_);
    peak_bytes_=std::max(peak_bytes_,pending_bytes_);ready_.notify_one();
  }
  void finish()
  {
    {std::lock_guard<std::mutex> lock(mutex_);closed_=true;ready_.notify_one();}
    if(worker_.joinable()){worker_.join();}
    std::lock_guard<std::mutex> lock(mutex_);joined_=true;
    if(!error_.empty()){throw std::runtime_error(error_);}
  }
  nlohmann::json report() const
  {
    std::lock_guard<std::mutex> lock(mutex_);
    return {{"scope","bounded_file_worker_no_ROS_clock_or_commands"},{"capacity",capacity_},
      {"maximum_bytes",maximum_bytes_},{"accepted",accepted_},{"written",written_},
      {"pending_records",accepted_-written_},{"pending_bytes",pending_bytes_},
      {"peak_records",peak_records_},{"peak_bytes",peak_bytes_},{"in_flight",in_flight_},
      {"closed",closed_},{"joined",joined_},{"error",error_},
      {"drained",done_ && accepted_==written_ && queue_.empty() && !in_flight_}};
  }
private:
  void fail_locked(const std::string & reason)
  {
    if(error_.empty()){error_=reason;}closed_=true;ready_.notify_one();
  }
  void run()
  {
    for(;;){
      std::string line;
      {
        std::unique_lock<std::mutex> lock(mutex_);
        ready_.wait(lock,[this]{return closed_ || !queue_.empty();});
        if(queue_.empty()){done_=true;return;}
        line=std::move(queue_.front());queue_.pop_front();in_flight_=true;
      }
      try{sink_(line);}
      catch(const std::exception & error){
        std::lock_guard<std::mutex> lock(mutex_);in_flight_=false;done_=true;
        fail_locked(std::string("trace_write:")+error.what());return;
      }catch(...){
        std::lock_guard<std::mutex> lock(mutex_);in_flight_=false;done_=true;
        fail_locked("trace_write:unknown");return;
      }
      {std::lock_guard<std::mutex> lock(mutex_);++written_;pending_bytes_-=line.size();in_flight_=false;}
    }
  }
  std::function<void(const std::string &)> sink_;
  const size_t capacity_,maximum_bytes_;
  mutable std::mutex mutex_;std::condition_variable ready_;std::deque<std::string> queue_;
  size_t accepted_{0},written_{0},pending_bytes_{0},peak_records_{0},peak_bytes_{0};
  bool closed_{false},joined_{false},done_{false},in_flight_{false};std::string error_;
  std::thread worker_;
};
}  // namespace integrated_robot_navigation_sensors
