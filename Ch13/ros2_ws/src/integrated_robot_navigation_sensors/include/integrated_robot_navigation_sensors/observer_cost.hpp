// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <nlohmann/json.hpp>
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <optional>
#include <stdexcept>
#include <time.h>

namespace integrated_robot_navigation_sensors
{
// Cumulative fixed-size diagnostics under the existing observer mutex. Not a
// clock source, physics CPU profiler, control input, or per-frame history.
class ObserverCost
{
public:
  enum Stage{Update,PostUpdate};
  void add(Stage stage,int64_t start_wall,int64_t end_wall,int64_t start_cpu,int64_t end_cpu)
  {
    if(end_wall<start_wall || end_cpu<start_cpu){throw std::invalid_argument("observer cost rollback");}
    auto & item=stages_.at(static_cast<size_t>(stage));
    ++item.calls;item.wall+=end_wall-start_wall;item.cpu+=end_cpu-start_cpu;
    item.maximum=std::max(item.maximum,end_wall-start_wall);
  }
  void boundary(int64_t update_finished,int64_t post_started)
  {
    if(post_started<update_finished){throw std::invalid_argument("observer phase ordering");}
    ++boundary_calls_;boundary_wall_+=post_started-update_finished;
    boundary_max_=std::max(boundary_max_,post_started-update_finished);
  }
  nlohmann::json report() const
  {
    auto row=[](const Counters & v){return nlohmann::json{{"calls",v.calls},
        {"wall_ns",v.wall},{"cpu_ns",v.cpu},{"max_wall_ns",v.maximum}};};
    return {{"scope","cumulative_owned_plugin_work_and_interphase_wall_not_physics_cpu"},
      {"update",row(stages_[0])},{"post_update",row(stages_[1])},{"errors",errors_},
      {"between_update_and_post",{{"calls",boundary_calls_},{"wall_ns",boundary_wall_},
        {"max_wall_ns",boundary_max_}}}};
  }
  class Scope
  {
  public:
    Scope(ObserverCost & owner,Stage stage,std::optional<int64_t> * end=nullptr)
    : owner_(owner),stage_(stage),end_(end),wall_(wall_now()),cpu_(cpu_now()){}
    Scope(const Scope &)=delete;
    ~Scope() noexcept
    {
      try{
        const auto cpu=cpu_now(),wall=wall_now();owner_.add(stage_,wall_,wall,cpu_,cpu);
        if(end_){*end_=wall;}
      }catch(...){++owner_.errors_;}
    }
    int64_t start_wall() const{return wall_;}
  private:
    static int64_t wall_now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();}
    static int64_t cpu_now(){timespec t{};
      if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t)!=0){throw std::runtime_error("observer CPU clock");}
      return static_cast<int64_t>(t.tv_sec)*1000000000+t.tv_nsec;}
    ObserverCost & owner_;Stage stage_;std::optional<int64_t> * end_;int64_t wall_,cpu_;
  };
private:
  struct Counters{uint64_t calls{0};int64_t wall{0},cpu{0},maximum{0};};
  std::array<Counters,2> stages_{};
  uint64_t boundary_calls_{0},errors_{0};int64_t boundary_wall_{0},boundary_max_{0};
};
}  // namespace integrated_robot_navigation_sensors
