// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/gazebo_observation.hpp"
#include <gz/sim/System.hh>
#include <gz/plugin/Register.hh>
#include <gz/transport/Node.hh>
#include <gz/msgs/boolean.pb.h>
#include <gz/msgs/empty.pb.h>
#include <gz/common/Console.hh>
#include <memory>
#include <mutex>
#include <optional>

namespace integrated_robot_navigation_sensors
{
struct EgressState
{
  std::mutex mutex;
  bool stopped{false};
};
class GazeboObserver : public gz::sim::System, public gz::sim::ISystemConfigure,
  public gz::sim::ISystemPreUpdate, public gz::sim::ISystemPostUpdate
{
public:
  void Configure(const gz::sim::Entity & entity,
    const std::shared_ptr<const sdf::Element> &, gz::sim::EntityComponentManager & ecm,
    gz::sim::EventManager &) override
  {
    model_ = entity;
    request_gazebo_observations(model_, ecm);
    com_ = node_.Advertise<gz::msgs::Pose>("/navigation/native_com");
    feet_ = node_.Advertise<gz::msgs::Pose_V>("/navigation/native_feet");
    contacts_ = node_.Advertise<gz::msgs::Contacts>("/navigation/native_contacts");
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
  void PostUpdate(const gz::sim::UpdateInfo & info,
    const gz::sim::EntityComponentManager & ecm) override
  {
    std::lock_guard<std::mutex> lock(state_->mutex);
    if (info.dt < std::chrono::steady_clock::duration::zero() ||
      (last_seen_ && info.simTime < *last_seen_)) {state_->stopped = true;}
    last_seen_ = info.simTime;
    if (state_->stopped || info.paused || (last_publish_ &&
      info.simTime-*last_publish_ < std::chrono::milliseconds(20))) {return;}
    try {
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
  std::optional<std::chrono::steady_clock::duration> last_seen_, last_publish_;
  std::shared_ptr<EgressState> state_{std::make_shared<EgressState>()};
  gz::transport::Node::Publisher com_, feet_, contacts_;
  gz::transport::Node node_;  // destroyed first; callbacks hold no raw plugin pointer
};
}  // namespace integrated_robot_navigation_sensors
GZ_ADD_PLUGIN(integrated_robot_navigation_sensors::GazeboObserver, gz::sim::System,
  gz::sim::ISystemConfigure, gz::sim::ISystemPreUpdate, gz::sim::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(integrated_robot_navigation_sensors::GazeboObserver,
  "integrated_robot_navigation_sensors::GazeboObserver")
