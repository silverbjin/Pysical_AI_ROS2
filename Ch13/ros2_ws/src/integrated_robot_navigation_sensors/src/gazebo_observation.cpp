// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/gazebo_observation.hpp"
#include "integrated_robot_navigation_sensors/position_reference.hpp"
#include <gz/sim/Util.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/Link.hh>
#include <gz/sim/components/AngularVelocity.hh>
#include <gz/sim/components/Pose.hh>
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
#include <algorithm>
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
std::optional<gz::msgs::StringMsg> encode_snapshot(std::optional<nlohmann::json> snapshot)
{
  if(!snapshot){return std::nullopt;}
  gz::msgs::StringMsg result;result.set_data(snapshot->dump());return result;
}
}
std::optional<nlohmann::json> read_gazebo_controls_json(gz::sim::Entity model,
  const gz::sim::EntityComponentManager & ecm,
  std::chrono::steady_clock::duration stamp, uint64_t sequence, bool require_commands)
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
        (require_commands && !has_velocity && !has_force)) {ready = false; return true;}
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
      if (const auto * reference=ecm.Component<PositionReference>(entity)) {
        const auto & values=reference->Data();
        if (values.size()!=4 || !std::all_of(values.begin(),values.end(),
            [](double value) {return std::isfinite(value);}) || values[3]<0.) {
          throw std::runtime_error("invalid native position reference diagnostic");
        }
        rows.back()["position_reference"]={{"source_input",values[0]},
          {"applied",values[1]},{"ramp_s",values[2]},
          {"write_capture_ns",static_cast<int64_t>(values[3])}};
      }
      return true;
    });
  if (!ready || rows.empty()) {return std::nullopt;}
  const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(stamp).count();
  if (ns < 0) {throw std::runtime_error("negative native capture");}
  return Json{{"schema", 2}, {"engine", "gazebo"}, {"capture_ns", ns},
    {"epoch", 0}, {"sequence", sequence}, {"joints", std::move(rows)}};
}
void request_gazebo_observations(gz::sim::Entity model, gz::sim::EntityComponentManager & ecm)
{
  const auto canonical = gz::sim::Model(model).CanonicalLink(ecm);
  if (canonical != gz::sim::kNullEntity) {
    // Requests native readback components only. No velocity/force setters.
    gz::sim::Link(canonical).EnableVelocityChecks(ecm);
  }
  std::vector<gz::sim::Entity> requested;
  ecm.Each<comp::Collision>([&](const gz::sim::Entity & entity, const comp::Collision *) {
    if (descendant(entity, model, ecm) && !ecm.Component<comp::ContactSensorData>(entity)) {
      requested.push_back(entity);
    }
    return true;
  });
  for (auto entity : requested) {ecm.CreateComponent(entity, comp::ContactSensorData());}
}
std::optional<nlohmann::json> read_gazebo_body_reference_json(gz::sim::Entity model,
  const gz::sim::EntityComponentManager & ecm,
  std::chrono::steady_clock::duration stamp, uint64_t sequence)
{
  const auto canonical = gz::sim::Model(model).CanonicalLink(ecm);
  if (canonical == gz::sim::kNullEntity) {return std::nullopt;}
  const auto * name = ecm.Component<comp::Name>(canonical);
  if (!name || name->Data() != "base_footprint") {
    throw std::runtime_error("native canonical frame is not base_footprint");
  }
  const auto * velocity = ecm.Component<comp::WorldAngularVelocity>(canonical);
  const auto * pose = ecm.Component<comp::WorldPose>(canonical);
  if (!velocity || !pose) {return std::nullopt;}
  const auto & rotation = pose->Data().Rot();
  const double norm = rotation.W()*rotation.W()+rotation.X()*rotation.X()+
    rotation.Y()*rotation.Y()+rotation.Z()*rotation.Z();
  const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(stamp).count();
  if (ns < 0 || !velocity->Data().IsFinite() || !pose->Data().IsFinite() ||
    !std::isfinite(norm) || std::abs(norm-1.) > 1e-9) {
    throw std::runtime_error("invalid native body reference time/velocity/pose");
  }
  const auto body = rotation.RotateVectorReverse(velocity->Data());
  return nlohmann::json{{"capture_ns",ns},{"epoch",0},{"sequence",sequence},
    {"frame_id","base_footprint"},{"source","gazebo_ecm_world_angular_velocity"},
    {"entity",canonical},{"angular_velocity",{body.X(),body.Y(),body.Z()}}};
}
std::optional<nlohmann::json> read_gazebo_contact_reference_json(gz::sim::Entity model,
  const gz::sim::EntityComponentManager & ecm, std::chrono::steady_clock::duration stamp,
  bool compact_when_supported)
{
  using Json = nlohmann::json;
  const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(stamp).count();
  if (ns < 0) {throw std::runtime_error("negative native contact capture");}
  const std::array<std::string,4> feet{"fr_foot","fl_foot","rr_foot","rl_foot"};
  std::array<const comp::ContactSensorData *,4> sources{};
  std::array<gz::sim::Entity,4> entities{};
  std::array<gz::math::Vector3d,4> centers;
  std::array<double,4> loads{};
  std::array<gz::math::Vector3d,4> collision_forces{};
  std::array<bool,4> collision_force_valid{true,true,true,true};
  ecm.Each<comp::Collision,comp::Name,comp::ContactSensorData>(
    [&](const gz::sim::Entity & entity,const comp::Collision *,const comp::Name * name,
      const comp::ContactSensorData * data) {
      if (!descendant(entity,model,ecm)) {return true;}
      for (size_t i=0;i<feet.size();++i) {
        if (name->Data().find("navcol__"+feet[i]+"__0")==std::string::npos) {continue;}
        if (sources[i]) {throw std::runtime_error("ambiguous native diagnostic foot collision");}
        const auto center = gz::sim::worldPose(entity,ecm).Pos();
        if (!center.IsFinite()) {throw std::runtime_error("nonfinite native diagnostic foot center");}
        sources[i]=data; entities[i]=entity; centers[i]=center;
        for (const auto & pair : data->Data().contact()) {
          for (const auto & wrench : pair.wrench()) {
            const auto & fa = wrench.body_1_wrench().force();
            const auto & fb = wrench.body_2_wrench().force();
            for (auto value : {fa.x(),fa.y(),fa.z(),fb.x(),fb.y(),fb.z()}) {
              if (!std::isfinite(value)) {throw std::runtime_error("nonfinite native diagnostic force");}
            }
            loads[i]+=std::abs(fa.z());
            // Diagnostic sum on this exact collision. Preserve tangential
            // signs/body ordering; do not promote it to a ground-mapped,
            // deduplicated FootContacts load or controller feedback.
            if (pair.collision1().id()==entity) {
              collision_forces[i]+=gz::math::Vector3d(fa.x(),fa.y(),fa.z());
            } else if (pair.collision2().id()==entity) {
              collision_forces[i]+=gz::math::Vector3d(fb.x(),fb.y(),fb.z());
            } else {
              collision_force_valid[i]=false;
            }
          }
        }
      }
      return true;
    });
  for (auto source : sources) {if (!source) {return std::nullopt;}}
  // This raw load heuristic selects diagnostic detail ONLY. It is not the
  // ground-mapped, deduplicated FootContacts support/acceptance calculation.
  const auto loaded=std::count_if(loads.begin(),loads.end(),[](double force){return force>=2.;});
  const bool details=!compact_when_supported || loaded<3;
  Json rows=Json::array();
  for (size_t i=0;i<feet.size();++i) {
    const auto & center=centers[i];
    Json row{{"name",feet[i]},{"entity",entities[i]},
      {"center_world",{center.X(),center.Y(),center.Z()}},
      {"pair_count",sources[i]->Data().contact_size()},{"sum_abs_force1_world_z_n",loads[i]}};
    row["force_on_collision_valid"]=collision_force_valid[i];
    const auto & force=collision_forces[i];
    row["sum_force_on_collision_world_n"]=collision_force_valid[i] ?
      Json::array({force.X(),force.Y(),force.Z()}) : Json(nullptr);
    if (details) {
      Json pairs=Json::array();
      for (const auto & pair : sources[i]->Data().contact()) {
        Json positions=Json::array(),depths=Json::array(),a=Json::array(),b=Json::array();
        for (const auto & p : pair.position()) {positions.push_back({p.x(),p.y(),p.z()});}
        for (auto depth : pair.depth()) {depths.push_back(depth);}
        for (const auto & wrench : pair.wrench()) {
          const auto & fa=wrench.body_1_wrench().force(); const auto & fb=wrench.body_2_wrench().force();
          a.push_back({fa.x(),fa.y(),fa.z()}); b.push_back({fb.x(),fb.y(),fb.z()});
        }
        pairs.push_back(Json{{"collision1_id",pair.collision1().id()},
          {"collision2_id",pair.collision2().id()},{"positions_world",positions},
          {"depths",depths},{"force1_world",a},{"force2_world",b}});
      }
      row["pairs"]=std::move(pairs);
    }
    rows.push_back(std::move(row));
  }
  return Json{{"capture_ns",ns},{"sample_phase","post_physics"},
    {"source","gazebo_ecm_raw_contact_sensor_data"},{"details_included",details},{"feet",std::move(rows)}};
}
std::optional<gz::msgs::StringMsg> read_gazebo_controls(gz::sim::Entity model,
  const gz::sim::EntityComponentManager & ecm,std::chrono::steady_clock::duration stamp,
  uint64_t sequence,bool require_commands)
{return encode_snapshot(read_gazebo_controls_json(model,ecm,stamp,sequence,require_commands));}
std::optional<gz::msgs::StringMsg> read_gazebo_body_reference(gz::sim::Entity model,
  const gz::sim::EntityComponentManager & ecm,std::chrono::steady_clock::duration stamp,uint64_t sequence)
{return encode_snapshot(read_gazebo_body_reference_json(model,ecm,stamp,sequence));}
std::optional<gz::msgs::StringMsg> read_gazebo_contact_reference(gz::sim::Entity model,
  const gz::sim::EntityComponentManager & ecm,std::chrono::steady_clock::duration stamp,bool compact_when_supported)
{return encode_snapshot(read_gazebo_contact_reference_json(model,ecm,stamp,compact_when_supported));}
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
