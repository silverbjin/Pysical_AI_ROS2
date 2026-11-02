// SPDX-License-Identifier: Apache-2.0
// Ch13-only bounded position force plus model-bound native implicit damping.
// Public gz_ros2_control ABI only; no copied/modified external implementation.
#include <gz_ros2_control/gz_system_interface.hpp>
#include <pluginlib/class_list_macros.hpp>
#include <gz/sim/components/JointAxis.hh>
#include <gz/sim/components/JointType.hh>
#include <gz/sim/components/JointPosition.hh>
#include <gz/sim/components/JointVelocity.hh>
#include <gz/sim/components/JointPositionReset.hh>
#include <gz/sim/components/JointTransmittedWrench.hh>
#include <gz/sim/components/JointVelocityCmd.hh>
#include <gz/sim/components/JointForceCmd.hh>
#include <algorithm>
#include <cmath>
#include <set>
#include <stdexcept>
#include <vector>
#include <optional>
#include <limits>
#include "integrated_robot_navigation_sensors/position_reference.hpp"

namespace integrated_robot_navigation_sensors
{
namespace comp = gz::sim::components;
using Return = hardware_interface::return_type;
using Callback = rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;

class PositionPDSystem final : public gz_ros2_control::GazeboSimSystemInterface
{
  struct Joint
  {
    std::string name;
    gz::sim::Entity entity;
    double lower, upper, effort, kp, kd;
    double position, velocity{0.}, command, hold;
    bool active{false};
    double ramp_seconds{0.}, applied{0.}, ramp_from{0.}, requested{0.};
    std::optional<int64_t> ramp_start;
  };
  std::vector<Joint> joints_;
  gz::sim::EntityComponentManager * ecm_{nullptr};
  bool measured_{false}, failed_{false};
  bool command_exported_{false};
  std::optional<int64_t> last_write_;

  static double number(const std::string & value)
  {
    size_t consumed = 0;
    const double result = std::stod(value, &consumed);
    if (consumed != value.size() || !std::isfinite(result)) {
      throw std::runtime_error("finite scalar parameter required");
    }
    return result;
  }
  Return fault(const std::string & why)
  {
    if (!failed_ && nh_) {RCLCPP_ERROR(nh_->get_logger(), "PositionPDSystem sticky fault: %s", why.c_str());}
    failed_ = true;
    if (ecm_) {
      for (const auto & joint : joints_) {
        ecm_->SetComponentData<comp::JointForceCmd>(joint.entity, {0.});
      }
    }
    return Return::ERROR;
  }
public:
  bool initSim(rclcpp::Node::SharedPtr & node, std::map<std::string, gz::sim::Entity> & native,
    const hardware_interface::HardwareInfo & info, gz::sim::EntityComponentManager & ecm,
    unsigned int update_rate) override
  {
    if (ecm_ || !node || !update_rate || info.joints.empty() || !info.mimic_joints.empty()) {return false;}
    std::vector<Joint> checked;
    std::set<std::string> names;
    try {
      const auto option = info.hardware_parameters.find("ch13_g1_reference_experiment");
      const bool experiment = option != info.hardware_parameters.end();
      if (experiment && option->second != "true") {
        throw std::runtime_error("explicit G1 reference experiment flag required");
      }
      size_t ramps = 0;
      for (const auto & source : info.joints) {
        if (!names.insert(source.name).second || source.command_interfaces.size() != 1 ||
          source.command_interfaces[0].name != "position" || source.state_interfaces.size() != 2) {
          throw std::runtime_error("unique scalar position interface required");
        }
        const auto entity = native.at(source.name);
        const auto * type = ecm.Component<comp::JointType>(entity);
        const auto * axis = ecm.Component<comp::JointAxis>(entity);
        if (!type || !axis || (type->Data() != sdf::JointType::REVOLUTE &&
          type->Data() != sdf::JointType::PRISMATIC) ||
          ecm.Component<comp::JointVelocityCmd>(entity) || ecm.Component<comp::JointForceCmd>(entity)) {
          throw std::runtime_error("native scalar joint missing or command owner already present");
        }
        const double lower = axis->Data().Lower(), upper = axis->Data().Upper();
        const double effort = axis->Data().Effort();
        if (!std::isfinite(lower) || !std::isfinite(upper) || lower >= upper ||
          !std::isfinite(effort) || effort <= 0.) {throw std::runtime_error("native finite limits required");}
        const auto & command = source.command_interfaces[0];
        if (std::abs(number(command.min)-lower) > 1e-9 ||
          std::abs(number(command.max)-upper) > 1e-9) {
          throw std::runtime_error("ROS/native position bound mismatch");
        }
        std::set<std::string> states;
        double initial = std::numeric_limits<double>::quiet_NaN();
        for (const auto & state : source.state_interfaces) {
          if (!states.insert(state.name).second) {throw std::runtime_error("duplicate state interface");}
          if (state.name == "position") {initial = number(state.initial_value);}
        }
        const double kp = number(source.parameters.at("ch13_kp"));
        const double kd = number(source.parameters.at("ch13_kd"));
        const double base_damping = number(source.parameters.at("ch13_base_damping"));
        const double native_damping = number(source.parameters.at("ch13_native_damping"));
        if (states != std::set<std::string>{"position", "velocity"} || kp <= 0. || kd <= 0. ||
          !std::isfinite(initial) || initial < lower || initial > upper) {
          throw std::runtime_error("finite position/velocity/initial/gain contract required");
        }
        if (source.parameters.at("ch13_damping_mode") != "native" || base_damping < 0. ||
          std::abs(native_damping-base_damping-kd) > 1e-9*(1.+native_damping) ||
          !std::isfinite(axis->Data().Damping()) ||
          std::abs(axis->Data().Damping()-native_damping) > 1e-9*(1.+native_damping)) {
          throw std::runtime_error("model-bound native damping required; no explicit fallback");
        }
        checked.push_back(Joint{source.name, entity, lower, upper, effort, kp, kd,
          initial, 0., initial, initial, false});
        auto & joint = checked.back();
        joint.applied = joint.ramp_from = joint.requested = initial;
        const auto ramp = source.parameters.find("ch13_reference_ramp_s");
        if (ramp != source.parameters.end()) {
          const bool leg = source.name.rfind("fr_",0)==0 || source.name.rfind("fl_",0)==0 ||
            source.name.rfind("rr_",0)==0 || source.name.rfind("rl_",0)==0;
          if (!experiment || !leg || std::abs(number(ramp->second)-.02)>1e-12) {
            throw std::runtime_error("only explicit G1 leg20ms reference is supported");
          }
          joint.ramp_seconds = .02;
          ++ramps;
        }
      }
      if (experiment && !ramps) {throw std::runtime_error("empty reference experiment");}
    } catch (const std::exception & error) {
      RCLCPP_ERROR(node->get_logger(), "PositionPDSystem initialization rejected: %s", error.what());
      return false;
    }
    // Validation is transactional. Initialize joints once, like native URDF
    // startup, never the root and never in a read/write or recovery callback.
    nh_ = node;
    ecm_ = &ecm;
    joints_ = std::move(checked);  // stable handle storage; never resized again
    for (const auto & joint : joints_) {
      if (!ecm.Component<comp::JointPosition>(joint.entity)) {
        ecm.CreateComponent(joint.entity, comp::JointPosition());
      }
      if (!ecm.Component<comp::JointVelocity>(joint.entity)) {
        ecm.CreateComponent(joint.entity, comp::JointVelocity());
      }
      if (!ecm.Component<comp::JointTransmittedWrench>(joint.entity)) {
        ecm.CreateComponent(joint.entity, comp::JointTransmittedWrench());
      }
      ecm.CreateComponent(joint.entity, comp::JointPositionReset({joint.position}));
      ecm.CreateComponent(joint.entity, comp::JointForceCmd({0.}));
      if (joint.ramp_seconds>0.) {
        ecm.CreateComponent(joint.entity, PositionReference({joint.command,joint.applied,joint.ramp_seconds,0.}));
      }
    }
    return true;
  }
  std::vector<hardware_interface::StateInterface> export_state_interfaces() override
  {
    std::vector<hardware_interface::StateInterface> result;
    for (auto & joint : joints_) {
      result.emplace_back(joint.name, "position", &joint.position);
      result.emplace_back(joint.name, "velocity", &joint.velocity);
    }
    return result;
  }
  std::vector<hardware_interface::CommandInterface> export_command_interfaces() override
  {
    std::vector<hardware_interface::CommandInterface> result;
    if (command_exported_ || !ecm_) {return result;}
    command_exported_ = true;
    for (auto & joint : joints_) {result.emplace_back(joint.name, "position", &joint.command);}
    return result;
  }
  Callback on_configure(const rclcpp_lifecycle::State &) override
  {return ecm_ && !failed_ ? Callback::SUCCESS : Callback::ERROR;}
  Callback on_activate(const rclcpp_lifecycle::State &) override
  {return ecm_ && !failed_ ? Callback::SUCCESS : Callback::ERROR;}
  Callback on_deactivate(const rclcpp_lifecycle::State &) override
  {return Callback::SUCCESS;}  // no reset/re-arm; engine pause/exit is a separate contract

  Return perform_command_mode_switch(const std::vector<std::string> & start,
    const std::vector<std::string> & stop) override
  {
    if (failed_ || !ecm_) {return Return::ERROR;}
    const std::set<std::string> starting(start.begin(), start.end()), stopping(stop.begin(), stop.end());
    if (starting.size() != start.size() || stopping.size() != stop.size()) {return Return::ERROR;}
    std::set<std::string> known;
    for (const auto & joint : joints_) {
      const auto name = joint.name+"/position";
      known.insert(name);
      if ((starting.count(name) && joint.active && !stopping.count(name)) ||
        (stopping.count(name) && !joint.active)) {return Return::ERROR;}
    }
    for (const auto & name : starting) {if (!known.count(name)) {return Return::ERROR;}}
    for (const auto & name : stopping) {if (!known.count(name)) {return Return::ERROR;}}
    for (auto & joint : joints_) {
      const auto name = joint.name+"/position";
      if (stopping.count(name)) {joint.active = false;}
      if (starting.count(name)) {joint.command = joint.hold; joint.active = true;}
    }
    return Return::OK;
  }
  Return read(const rclcpp::Time &, const rclcpp::Duration &) override
  {
    if (!ecm_ || failed_) {return Return::ERROR;}
    bool complete = true;
    for (auto & joint : joints_) {
      const auto * q = ecm_->Component<comp::JointPosition>(joint.entity);
      const auto * qd = ecm_->Component<comp::JointVelocity>(joint.entity);
      if (!q || q->Data().empty() || !qd || qd->Data().empty()) {complete = false; continue;}
      if (q->Data().size() != 1 || qd->Data().size() != 1 || !std::isfinite(q->Data()[0]) ||
        !std::isfinite(qd->Data()[0])) {return fault("invalid native state");}
      joint.position = q->Data()[0]; joint.velocity = qd->Data()[0];
    }
    if (measured_ && !complete) {return fault("native state disappeared");}
    measured_ = complete;
    return Return::OK;  // initial URDF seeds are never native acceptance evidence
  }
  Return write(const rclcpp::Time & time, const rclcpp::Duration & period) override
  {
    if (failed_ || !ecm_) {return Return::ERROR;}
    if (last_write_ && time.nanoseconds() < *last_write_) {return fault("clock rollback");}
    last_write_ = time.nanoseconds();
    // Read live scalar state at the physics step, not a stale controller-period
    // sample. No root setter, external wrench, velocity/position runtime reset.
    if (read(time, period) != Return::OK) {return Return::ERROR;}
    if (!measured_) {return Return::OK;}
    std::vector<double> forces;
    for (auto & joint : joints_) {
      if (ecm_->Component<comp::JointVelocityCmd>(joint.entity)) {return fault("competing native velocity owner");}
      const double target = joint.active ? joint.command : joint.hold;
      if (!std::isfinite(target) || target < joint.lower || target > joint.upper) {
        return fault("nonfinite or out-of-bound position command");
      }
      // DART integrates the declared native damper implicitly. Adding -kd*qd
      // here is explicit derivative feedback and would double-count damping.
      // This cap applies to external position force, not passive/contact wrench.
      if (joint.ramp_seconds == 0. || !joint.active) {
        joint.applied = joint.ramp_from = joint.requested = target;
        joint.ramp_start.reset();
      } else {
        if (joint.ramp_start) {
          const double elapsed = (time.nanoseconds()-*joint.ramp_start)/1e9;
          const double weight = std::clamp(elapsed/joint.ramp_seconds,0.,1.);
          joint.applied = joint.ramp_from*(1.-weight)+joint.requested*weight;
        }
        if (target != joint.requested) {
          joint.ramp_from = joint.applied;
          joint.requested = target;
          joint.ramp_start = time.nanoseconds();
        }
      }
      const double force = joint.kp*(joint.applied-joint.position);
      if (!std::isfinite(force)) {return fault("nonfinite internal effort");}
      forces.push_back(std::clamp(force, -joint.effort, joint.effort));
    }
    for (size_t i = 0; i < joints_.size(); ++i) {
      auto & joint = joints_[i];
      if (joint.active) {joint.hold = joint.applied;}
      ecm_->SetComponentData<comp::JointForceCmd>(joint.entity, {forces[i]});
      if (joint.ramp_seconds>0.) {
        ecm_->SetComponentData<PositionReference>(joint.entity,
          {joint.active ? joint.command : joint.hold,joint.applied,joint.ramp_seconds,
            static_cast<double>(time.nanoseconds())});
      }
    }
    return Return::OK;
  }
};
}  // namespace integrated_robot_navigation_sensors

PLUGINLIB_EXPORT_CLASS(integrated_robot_navigation_sensors::PositionPDSystem,
  gz_ros2_control::GazeboSimSystemInterface)
