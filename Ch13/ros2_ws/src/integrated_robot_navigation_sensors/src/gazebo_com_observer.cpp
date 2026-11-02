// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/gazebo_observation.hpp"
#include "integrated_robot_navigation_sensors/contact_detail_window.hpp"
#include "integrated_robot_navigation_sensors/dart_contact.hpp"
#include "integrated_robot_navigation_sensors/observer_cost.hpp"
#include <gz/sim/components/World.hh>
#include <gz/sim/System.hh>
#include <gz/plugin/Register.hh>
#include <gz/transport/Node.hh>
#include <gz/msgs/boolean.pb.h>
#include <gz/msgs/empty.pb.h>
#include <gz/common/Console.hh>
#include <memory>
#include <mutex>
#include <optional>
#include <nlohmann/json.hpp>
#include <vector>

namespace integrated_robot_navigation_sensors
{
struct EgressState
{
  std::mutex mutex;
  bool stopped{false};
};
class GazeboObserver : public gz::sim::System, public gz::sim::ISystemConfigure,
  public gz::sim::ISystemConfigurePriority, public gz::sim::ISystemPreUpdate,
  public gz::sim::ISystemUpdate, public gz::sim::ISystemPostUpdate
{
public:
  gz::sim::System::PriorityType ConfigurePriority() override
  {
    // All controller PreUpdate writes have completed. Read before Physics
    // Update(priority0) consumes and then clears native command components.
    return gz::sim::System::kDefaultPriority-1;
  }
  void Configure(const gz::sim::Entity & entity,
    const std::shared_ptr<const sdf::Element> & settings, gz::sim::EntityComponentManager & ecm,
    gz::sim::EventManager &) override
  {
    model_ = entity;
    const bool allowance=settings && settings->HasElement("g1_contact_allowance_m");
    const bool explicit_flag=settings && settings->HasElement("g1_validation_contact_experiment");
    if (allowance!=explicit_flag) {throw std::runtime_error("incomplete G1 contact experiment settings");}
    if (allowance) {
      size_t worlds=0;
      ecm.Each<gz::sim::components::World>([&](gz::sim::Entity,const gz::sim::components::World *) {
        ++worlds;return true;
      });
      const double requested=settings->Get<double>("g1_contact_allowance_m");
      const auto actual=configure_g1_dart_contact(requested,worlds,
        settings->Get<bool>("g1_validation_contact_experiment"));
      dart_contact_=nlohmann::json{{"schema",1},{"mode","allowance50um"},
        {"requested_m",requested},{"before_m",actual.before_m},{"effective_m",actual.effective_m},
        {"world_count",worlds},{"explicit_g1",true},
        {"header_version",actual.header_version},{"library_path",actual.library_path}};
    }
    request_gazebo_observations(model_, ecm);
    com_ = node_.Advertise<gz::msgs::Pose>("/navigation/native_com");
    feet_ = node_.Advertise<gz::msgs::Pose_V>("/navigation/native_feet");
    contacts_ = node_.Advertise<gz::msgs::Contacts>("/navigation/native_contacts");
    controls_ = node_.Advertise<gz::msgs::StringMsg>("/navigation/native_controls");
    const std::weak_ptr<EgressState> weak = state_;
    std::function<bool(const gz::msgs::Empty &, gz::msgs::Boolean &)> stop =
      [weak](const gz::msgs::Empty &, gz::msgs::Boolean & response) {
        if (auto state = weak.lock()) {
          std::lock_guard<std::mutex> lock(state->mutex);
          state->stopped = true; response.set_data(true); return true;
        }
        response.set_data(false); return false;
      };
    node_.Advertise("/navigation/stop_native_observer", stop);
  }
  void PreUpdate(const gz::sim::UpdateInfo &, gz::sim::EntityComponentManager & ecm) override
  {
    if (!requested_) {request_gazebo_observations(model_, ecm); requested_ = true;}
  }
  void Update(const gz::sim::UpdateInfo & info, gz::sim::EntityComponentManager & ecm) override
  {
    std::lock_guard<std::mutex> lock(state_->mutex);
    ObserverCost::Scope measured_work(cost_,ObserverCost::Update,&update_finished_);
    if (info.dt < std::chrono::steady_clock::duration::zero() ||
      (last_seen_ && info.simTime < *last_seen_)) {state_->stopped = true;}
    if (state_->stopped || info.paused || (last_controls_publish_ &&
      info.simTime-*last_controls_publish_ < std::chrono::milliseconds(20))) {return;}
    try {
      auto controls = read_gazebo_controls_json(model_, ecm, info.simTime, controls_sequence_+1);
      if (controls_seen_ && !controls) {
        throw std::runtime_error("native joint command/state observation disappeared");
      }
      if (controls) {
        auto packet = std::move(*controls);
        const auto step_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(info.dt).count();
        const auto capture_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(info.simTime).count();
        if (capture_ns < step_ns) {throw std::runtime_error("native pre-physics state time underflow");}
        // Command applies to this step; ECM q/qd/wrench still describe the
        // previous completed physics step. Never label them as post-step state.
        packet["sample_phase"] = "pre_physics";
        packet["state_capture_ns"] = capture_ns-step_ns;
        packet["step_ns"] = step_ns;
        // Previous completed PostUpdates, each with its own original capture.
        // Batching avoids a new 500Hz Python/ROS subscriber. Never interpolate.
        packet["body_references"] = std::move(body_references_);
        // Completed preceding callbacks only. Neither cumulative timing nor
        // the interphase wall span is a sensor capture or a physics CPU claim.
        packet["observer_work"] = cost_.report();
        if (dart_contact_) {
          if (inspect_dart_contact().effective_m!=(*dart_contact_)["effective_m"].get<double>()) {
            throw std::runtime_error("DART contact allowance changed after configuration");
          }
          packet["dart_contact_configuration"]=*dart_contact_;
        }
        gz::msgs::StringMsg message;
        message.set_data(packet.dump());
        controls_.Publish(message);
        body_references_.clear();
        controls_seen_ = true;
        ++controls_sequence_;
        last_controls_publish_ = info.simTime;
      }
    } catch (const std::exception & error) {
      state_->stopped = true;
      gzerr << "Navigation control observation failed closed; restart required: " << error.what() << '\n';
    }
  }
  void PostUpdate(const gz::sim::UpdateInfo & info,
    const gz::sim::EntityComponentManager & ecm) override
  {
    std::lock_guard<std::mutex> lock(state_->mutex);
    ObserverCost::Scope measured_work(cost_,ObserverCost::PostUpdate);
    if(update_finished_){cost_.boundary(*update_finished_,measured_work.start_wall());}
    if (info.dt < std::chrono::steady_clock::duration::zero() ||
      (last_seen_ && info.simTime < *last_seen_)) {state_->stopped = true;}
    last_seen_ = info.simTime;
    if (state_->stopped || info.paused) {return;}
    try {
      if (controls_seen_ && (!last_body_ || info.simTime > *last_body_)) {
        auto reference = read_gazebo_body_reference_json(model_,ecm,info.simTime,body_sequence_+1);
        if (!reference) {throw std::runtime_error("native instantaneous body reference unavailable");}
        if (body_references_.size() >= 64) {throw std::runtime_error("native body reference batch overflow");}
        auto packet = std::move(*reference);
        auto contacts = read_gazebo_contact_reference_json(model_,ecm,info.simTime,true);
        if (!contacts) {throw std::runtime_error("native raw contact reference unavailable");}
        packet["raw_contacts"] = std::move(*contacts);
        unsigned loaded_mask=0,index=0;
        for (const auto & foot : packet["raw_contacts"]["feet"]) {
          if (foot["sum_abs_force1_world_z_n"].get<double>()>=2.) {loaded_mask|=1u<<index;}
          ++index;
        }
        const bool event=contact_detail_.observe(loaded_mask);
        packet["contact_event_window"]=event;
        if (event) {
          if (!packet["raw_contacts"]["details_included"].get<bool>()) {
            auto details=read_gazebo_contact_reference_json(model_,ecm,info.simTime,false);
            if (!details) {throw std::runtime_error("contact event detail unavailable");}
            packet["raw_contacts"]=std::move(*details);
          }
          auto joints=read_gazebo_controls_json(model_,ecm,info.simTime,controls_sequence_,false);
          if (!joints) {throw std::runtime_error("contact event joint snapshot unavailable");}
          auto snapshot=std::move(*joints);
          snapshot["sample_phase"]="post_physics_debug";
          snapshot["state_capture_ns"]=packet["capture_ns"];
          // Forces/references were applied BEFORE this completed step. Each
          // reference retains its actual write_capture_ns; do not relabel it.
          packet["contact_event_joints"]=std::move(snapshot);
        }
        body_references_.push_back(std::move(packet));
        ++body_sequence_;
        last_body_ = info.simTime;
      }
      if (last_publish_ && info.simTime-*last_publish_ < std::chrono::milliseconds(20)) {return;}
      const auto observation = read_gazebo_observations(model_, ecm, info.simTime);
      com_.Publish(observation.com); feet_.Publish(observation.feet);
      contacts_.Publish(observation.contacts); last_publish_ = info.simTime;
    } catch (const std::exception & error) {
      state_->stopped = true;
      gzerr << "Navigation observation failed closed; restart required: " << error.what() << '\n';
    }
  }
private:
  gz::sim::Entity model_{gz::sim::kNullEntity};
  bool requested_{false};
  bool controls_seen_{false};
  uint64_t controls_sequence_{0};
  uint64_t body_sequence_{0};
  std::vector<nlohmann::json> body_references_;
  ContactDetailWindow contact_detail_;
  std::optional<nlohmann::json> dart_contact_;
  std::optional<std::chrono::steady_clock::duration> last_body_;
  std::optional<std::chrono::steady_clock::duration> last_seen_, last_publish_;
  std::optional<std::chrono::steady_clock::duration> last_controls_publish_;
  ObserverCost cost_;
  std::optional<int64_t> update_finished_;
  std::shared_ptr<EgressState> state_{std::make_shared<EgressState>()};
  gz::transport::Node::Publisher com_, feet_, contacts_, controls_;
  gz::transport::Node node_;  // destroyed first; callbacks hold no raw plugin pointer
};
}  // namespace integrated_robot_navigation_sensors
GZ_ADD_PLUGIN(integrated_robot_navigation_sensors::GazeboObserver, gz::sim::System,
  gz::sim::ISystemConfigure, gz::sim::ISystemConfigurePriority, gz::sim::ISystemPreUpdate,
  gz::sim::ISystemUpdate, gz::sim::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(integrated_robot_navigation_sensors::GazeboObserver,
  "integrated_robot_navigation_sensors::GazeboObserver")
