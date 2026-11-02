// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <rclcpp/serialized_message.hpp>
#include <nlohmann/json.hpp>
#include <zlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
#include <condition_variable>
#include <deque>
#include <mutex>
#include <thread>
#include <stdexcept>

namespace integrated_robot_navigation_sensors {
class CdrJournal {
  using Json=nlohmann::json;
  struct Record {Json meta;std::shared_ptr<const rclcpp::SerializedMessage> data;size_t bytes;};
public:
  explicit CdrJournal(const std::string & path,size_t max_records=256,size_t max_bytes=8*1024*1024)
  : max_records_(max_records),max_bytes_(max_bytes) {
    if (!max_records || !max_bytes) {throw std::invalid_argument("CDR queue capacity");}
    fd_=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);
    if (fd_<0) {throw std::runtime_error("CDR file create/ownership");}
    try {write_all("CH13CDR1\n",9);worker_=std::thread([this]{run();});}
    catch (...) {::close(fd_);fd_=-1;throw;}
  }
  ~CdrJournal() {close();}
  bool submit(Json meta,std::shared_ptr<const rclcpp::SerializedMessage> data=nullptr) {
    const size_t bytes=1024+(data?data->capacity():0);
    std::lock_guard<std::mutex> lock(mutex_);
    if (closing_ || !error_.empty()) {return false;}
    if (queue_.size()>=max_records_ || bytes>max_bytes_ || queued_bytes_>max_bytes_-bytes) {
      error_="CDR bounded queue overflow";return false;
    }
    meta["sequence"]=++submitted_;queued_bytes_+=bytes;
    queue_.push_back({std::move(meta),std::move(data),bytes});condition_.notify_one();return true;
  }
  void close() noexcept {
    {std::lock_guard<std::mutex> lock(mutex_);closing_=true;condition_.notify_one();}
    if (worker_.joinable()) {worker_.join();}
    std::lock_guard<std::mutex> lock(mutex_);
    if (fd_>=0) {
      if (::close(fd_)!=0 && error_.empty()) {error_="CDR close failed";}
      fd_=-1;
    }
    joined_=true;
  }
  Json report() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return {{"submitted",submitted_},{"written",written_},{"error",error_},{"joined",joined_},
      {"pending_records",queue_.size()},{"pending_bytes",queued_bytes_},
      {"max_records",max_records_},{"max_bytes",max_bytes_}};
  }
private:
  static void u32(std::string & out,uint32_t value) {
    for(unsigned i=0;i<4;++i) {out.push_back(static_cast<char>((value>>(8*i))&255));}
  }
  void write_all(const char * data,size_t size) {
    while(size) {
      const auto count=::write(fd_,data,size);
      if(count<0 && errno==EINTR) {continue;}
      if(count<=0) {throw std::runtime_error("CDR write failed");}
      data+=count;size-=static_cast<size_t>(count);
    }
  }
  void write_record(const Record & row) {
    const auto meta=row.meta.dump();
    if(meta.size()>65536) {throw std::runtime_error("CDR metadata capacity");}
    std::string body;u32(body,static_cast<uint32_t>(meta.size()));body+=meta;
    if(row.data) {
      const auto & raw=row.data->get_rcl_serialized_message();
      body.append(reinterpret_cast<const char *>(raw.buffer),raw.buffer_length);
    }
    if(body.size()>8*1024*1024) {throw std::runtime_error("CDR record capacity");}
    std::string prefix;u32(prefix,static_cast<uint32_t>(body.size()));
    u32(prefix,static_cast<uint32_t>(crc32(0,reinterpret_cast<const Bytef *>(body.data()),body.size())));
    write_all(prefix.data(),prefix.size());write_all(body.data(),body.size());
  }
  void run() noexcept {
    try {
      while(true) {
        Record row;bool footer=false;
        {
          std::unique_lock<std::mutex> lock(mutex_);
          condition_.wait(lock,[this]{return closing_ || !queue_.empty();});
          if(queue_.empty()) {
            footer=true;row.meta={{"kind","end"},{"records",submitted_},{"sequence",submitted_+1}};
            ++submitted_;
          } else {
            row=std::move(queue_.front());queue_.pop_front();queued_bytes_-=row.bytes;
          }
        }
        write_record(row);
        {std::lock_guard<std::mutex> lock(mutex_);++written_;}
        if(footer) {break;}
      }
    } catch(const std::exception & error) {
      std::lock_guard<std::mutex> lock(mutex_);if(error_.empty()) {error_=error.what();}
    }
  }
  int fd_=-1;const size_t max_records_,max_bytes_;
  mutable std::mutex mutex_;std::condition_variable condition_;std::deque<Record> queue_;
  std::thread worker_;size_t queued_bytes_=0;uint64_t submitted_=0,written_=0;
  bool closing_=false,joined_=false;std::string error_;
};
}  // namespace integrated_robot_navigation_sensors
