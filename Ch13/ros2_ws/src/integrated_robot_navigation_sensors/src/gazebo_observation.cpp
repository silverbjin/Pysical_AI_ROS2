// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/gazebo_observation.hpp"
#include <gz/sim/Util.hh>
#include <gz/sim/components/Collision.hh>
#include <gz/sim/components/ContactSensorData.hh>
#include <gz/sim/components/Inertial.hh>
#include <gz/sim/components/Link.hh>
#include <gz/sim/components/Name.hh>
#include <array>
#include <cmath>
#include <set>
#include <stdexcept>
#include <vector>

namespace integrated_robot_navigation_sensors
{
namespace
{
namespace comp = gz::sim::components;
bool descendant(gz::sim::Entity child, gz::sim::Entity model,
  const gz::sim::EntityComponentManager & ecm)
{
  while (child != gz::sim::kNullEntity) {
    if (child == model) {return true;}
    child = ecm.ParentEntity(child);
  }
  return false;
}
void header(gz::msgs::Header * target, std::chrono::steady_clock::duration stamp)
{
  const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(stamp).count();
  target->mutable_stamp()->set_sec(ns/1000000000);
  target->mutable_stamp()->set_nsec(ns%1000000000);
  auto * frame = target->add_data(); frame->set_key("frame_id"); frame->add_value("odom");
}
std::string collision_name(gz::sim::Entity entity, const gz::sim::EntityComponentManager & ecm)
{
  auto name = gz::sim::scopedName(entity, ecm, "::", false);
  // Strip the actual world's scope, never guess fixed-joint collision suffixes.
  auto root = entity;
  while (ecm.ParentEntity(root) != gz::sim::kNullEntity) {root = ecm.ParentEntity(root);}
  const auto * component = ecm.Component<comp::Name>(root);
  const std::string prefix = component ? component->Data()+"::" : "";
  if (!prefix.empty() && name.rfind(prefix, 0) == 0) {name.erase(0, prefix.size());}
  return name;
}
void point(gz::msgs::Vector3d * target, const gz::math::Vector3d & value)
{
  target->set_x(value.X()); target->set_y(value.Y()); target->set_z(value.Z());
}
}
void request_gazebo_observations(gz::sim::Entity model, gz::sim::EntityComponentManager & ecm)
{
  std::vector<gz::sim::Entity> requested;
  ecm.Each<comp::Collision>([&](const gz::sim::Entity & entity, const comp::Collision *) {
    if (descendant(entity, model, ecm) && !ecm.Component<comp::ContactSensorData>(entity)) {
      requested.push_back(entity);
    }
    return true;
  });
  for (auto entity : requested) {ecm.CreateComponent(entity, comp::ContactSensorData());}
}
GazeboObservation read_gazebo_observations(gz::sim::Entity model,
  const gz::sim::EntityComponentManager & ecm, std::chrono::steady_clock::duration stamp)
{
  GazeboObservation result;
  header(result.com.mutable_header(), stamp);
  header(result.feet.mutable_header(), stamp);
  header(result.contacts.mutable_header(), stamp);
  double mass = 0.;
  gz::math::Vector3d weighted{0, 0, 0};
  ecm.Each<comp::Link, comp::Inertial>([&](const gz::sim::Entity & entity,
    const comp::Link *, const comp::Inertial * inertial) {
    if (!descendant(entity, model, ecm)) {return true;}
    const double value = inertial->Data().MassMatrix().Mass();
    if (!std::isfinite(value) || value < 0.) {throw std::runtime_error("invalid native link mass");}
    const auto pose = gz::sim::worldPose(entity, ecm);
    const auto com = pose.Pos() + pose.Rot().RotateVector(inertial->Data().Pose().Pos());
    if (!com.IsFinite()) {throw std::runtime_error("invalid native link pose");}
    mass += value; weighted += value*com;
    return true;
  });
  if (mass <= 0.) {throw std::runtime_error("no observed native robot mass");}
  point(result.com.mutable_position(), weighted/mass);
  result.com.mutable_orientation()->set_w(1.);
  const std::array<std::string, 4> feet{"fr_foot", "fl_foot", "rr_foot", "rl_foot"};
  std::array<gz::math::Vector3d, 4> foot_points;
  std::array<bool, 4> found{};
  std::set<std::pair<uint64_t, uint64_t>> pairs;
  ecm.Each<comp::Collision, comp::Name, comp::ContactSensorData>(
    [&](const gz::sim::Entity & entity, const comp::Collision *, const comp::Name * name,
      const comp::ContactSensorData * data) {
      if (!descendant(entity, model, ecm)) {return true;}
      for (size_t i = 0; i < feet.size(); ++i) {
        if (name->Data().find("navcol__"+feet[i]+"__0") != std::string::npos) {
          if (found[i]) {throw std::runtime_error("ambiguous native foot collision");}
          found[i] = true; foot_points[i] = gz::sim::worldPose(entity, ecm).Pos();
        }
      }
      for (const auto & source : data->Data().contact()) {
        const auto a = source.collision1().id(), b = source.collision2().id();
        if (!pairs.emplace(std::min(a, b), std::max(a, b)).second) {continue;}
        auto * contact = result.contacts.add_contact();
        contact->CopyFrom(source);
        contact->mutable_collision1()->set_name(collision_name(a, ecm));
        contact->mutable_collision2()->set_name(collision_name(b, ecm));
      }
      return true;
    });
  for (size_t i = 0; i < feet.size(); ++i) {
    if (!found[i]) {throw std::runtime_error("missing actual native foot collision");}
    auto * foot = result.feet.add_pose(); foot->set_name(feet[i]);
    point(foot->mutable_position(), foot_points[i]); foot->mutable_orientation()->set_w(1.);
  }
  return result;
}
}  // namespace integrated_robot_navigation_sensors
