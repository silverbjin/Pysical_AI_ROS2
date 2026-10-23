// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/gazebo_observation.hpp"
#include <gz/sim/Util.hh>
#include <gz/sim/components/Collision.hh>
#include <gz/sim/components/ContactSensorData.hh>
#include <gz/sim/components/Inertial.hh>
#include <gz/sim/components/Link.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/components/JointAxis.hh>
#include <gz/sim/components/JointType.hh>
#include <gz/sim/components/JointPosition.hh>
#include <gz/sim/components/JointVelocity.hh>
#include <gz/sim/components/JointVelocityCmd.hh>
#include <gz/sim/components/JointForce.hh>
#include <gz/sim/components/JointForceCmd.hh>
#include <gz/sim/components/JointTransmittedWrench.hh>
#include <nlohmann/json.hpp>
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
std::optional<gz::msgs::StringMsg> read_gazebo_controls(gz::sim::Entity model,
  const gz::sim::EntityComponentManager & ecm,
  std::chrono::steady_clock::duration stamp, uint64_t sequence)
{
  using Json = nlohmann::json;
  Json rows = Json::array();
  bool ready = true;
  auto scalar = [](const std::vector<double> & values) {
      if (values.size() != 1 || !std::isfinite(values[0])) {
        throw std::runtime_error("nonfinite or non-scalar actual native joint value");
      }
      return values[0];
    };
  ecm.Each<comp::JointType, comp::JointAxis, comp::Name>(
    [&](const gz::sim::Entity & entity, const comp::JointType * type,
      const comp::JointAxis * axis, const comp::Name * name) {
      if (!descendant(entity, model, ecm)) {return true;}
      const bool hinge = type->Data() == sdf::JointType::REVOLUTE;
      if (!hinge && type->Data() != sdf::JointType::PRISMATIC) {
        if (type->Data() != sdf::JointType::FIXED) {
          throw std::runtime_error("unsupported non-scalar native joint");
        }
        return true;
      }
      const auto * q = ecm.Component<comp::JointPosition>(entity);
      const auto * qd = ecm.Component<comp::JointVelocity>(entity);
      const auto * velocity = ecm.Component<comp::JointVelocityCmd>(entity);
      const auto * force = ecm.Component<comp::JointForceCmd>(entity);
      const auto * wrench = ecm.Component<comp::JointTransmittedWrench>(entity);
      const bool has_velocity = velocity && !velocity->Data().empty();
      const bool has_force = force && !force->Data().empty();
      if (!q || q->Data().empty() || !qd || qd->Data().empty() || !wrench ||
        (!has_velocity && !has_force)) {ready = false; return true;}
      const auto a = axis->Data().Xyz();
      const auto & w = wrench->Data();
      const std::vector<double> torque{w.torque().x(), w.torque().y(), w.torque().z()};
      const std::vector<double> transmitted_force{w.force().x(), w.force().y(), w.force().z()};
      for (auto value : {a.X(), a.Y(), a.Z(), axis->Data().Effort(),
          axis->Data().MaxVelocity(), axis->Data().Lower(), axis->Data().Upper(), axis->Data().Damping(),
          torque[0], torque[1], torque[2], transmitted_force[0], transmitted_force[1],
          transmitted_force[2]}) {
        if (!std::isfinite(value)) {throw std::runtime_error("nonfinite native joint metadata/wrench");}
      }
      if (axis->Data().Damping() < 0.) {throw std::runtime_error("negative native damping");}
      const auto & projected = hinge ? torque : transmitted_force;
      Json applied = nullptr;
      const auto * actual_force = ecm.Component<comp::JointForce>(entity);
      if (actual_force && !actual_force->Data().empty()) {applied = scalar(actual_force->Data());}
      rows.push_back(Json{{"entity", entity}, {"name", name->Data()},
        {"type", hinge ? "hinge" : "slide"}, {"axis_joint", {a.X(), a.Y(), a.Z()}},
        {"position", scalar(q->Data())}, {"velocity", scalar(qd->Data())},
        {"position_unit", hinge ? "rad" : "m"}, {"velocity_unit", hinge ? "rad/s" : "m/s"},
        {"effort_unit", hinge ? "Nm" : "N"}, {"effort_limit", axis->Data().Effort()},
        {"native_damping", axis->Data().Damping()},
        {"velocity_limit", axis->Data().MaxVelocity()}, {"lower", axis->Data().Lower()},
        {"upper", axis->Data().Upper()},
        {"velocity_command", has_velocity ? Json(scalar(velocity->Data())) : Json(nullptr)},
        {"force_command", has_force ? Json(scalar(force->Data())) : Json(nullptr)},
        {"transmitted_force_joint", transmitted_force}, {"transmitted_torque_joint", torque},
        {"projected_transmitted_effort", a.X()*projected[0]+a.Y()*projected[1]+a.Z()*projected[2]},
        {"applied_generalized_force", applied}});
      return true;
    });
  if (!ready || rows.empty()) {return std::nullopt;}
  const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(stamp).count();
  if (ns < 0) {throw std::runtime_error("negative native capture");}
  gz::msgs::StringMsg result;
  result.set_data(Json{{"schema", 2}, {"engine", "gazebo"}, {"capture_ns", ns},
    {"epoch", 0}, {"sequence", sequence}, {"joints", rows}}.dump());
  return result;
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
