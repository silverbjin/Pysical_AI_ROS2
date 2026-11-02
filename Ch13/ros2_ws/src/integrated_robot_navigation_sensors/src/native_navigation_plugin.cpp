// SPDX-License-Identifier: Apache-2.0
// Capture-time encoding below adapts MuJoCoSimulation::publish_clock(),
// mujoco_ros2_control c261f5552edf124d1000a23fb25b6c07cadeb807 (Apache-2.0).
// Copyright (c) 2025, United States Government, as represented by the
// Administrator of the National Aeronautics and Space Administration.
// All rights reserved. See REUSE_MANIFEST.md and LICENSE.
#include "integrated_robot_navigation_sensors/snapshot.hpp"
#include "integrated_robot_navigation_sensors/normalization.hpp"
#include "integrated_robot_navigation_sensors/command_trace.hpp"
#include "integrated_robot_navigation_sensors/applied_reference.hpp"
#include "mujoco_ros2_control_plugins/mujoco_ros2_control_plugins_base.hpp"
#include <pluginlib/class_list_macros.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <integrated_robot_interfaces/msg/foot_contacts.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <sensor_msgs/msg/laser_scan.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <std_msgs/msg/string.hpp>
#include <nlohmann/json.hpp>
#include <algorithm>
#include <cmath>
#include <limits>
#include <chrono>

namespace integrated_robot_navigation_sensors
{
namespace
{
struct Publishers
{
  rclcpp::Publisher<integrated_robot_interfaces::msg::FootContacts>::SharedPtr feet;
  rclcpp::Publisher<sensor_msgs::msg::Imu>::SharedPtr imu;
  rclcpp::Publisher<sensor_msgs::msg::LaserScan>::SharedPtr scan;
  rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr com;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr controls;
  double last_scan{-std::numeric_limits<double>::infinity()};
};
struct PluginState
{
  std::mutex mutex;
  std::shared_ptr<SensorWorker> worker;
  std::shared_ptr<AppliedReferenceWorker> applied_worker;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr stop_service, health_service;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr trace_service;
  NativeCommandTrace trace;
  std::vector<std::string> trace_names;
  std::vector<int> trace_ctrl_indices, trace_dof_indices;
  double last_observed{-std::numeric_limits<double>::infinity()};
  double last_submitted{-std::numeric_limits<double>::infinity()};
  bool stopped{false};
  std::string reason;
};
void trace_numeric(PluginState & state, const mjData * data, bool physics)
{
  if (!state.trace.accepting.load(std::memory_order_acquire)) {return;}
  if (!std::isfinite(data->time) || data->time < 0.) {++state.trace.invalid_time; return;}
  CommandTraceRow row;
  row.snapshot_ros_ns = static_cast<int64_t>(std::llround(data->time*1e9));
  row.steady_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::steady_clock::now().time_since_epoch()).count();
  for (size_t i = 0; i < state.trace_names.size(); ++i) {
    row.ctrl[i] = data->ctrl[state.trace_ctrl_indices[i]];
    row.joint_velocity[i] = data->qvel[state.trace_dof_indices[i]];
  }
  for (size_t i = 0; i < 3; ++i) {row.body_angular_velocity[i] = data->qvel[3+i];}
  (physics ? state.trace.pre_step : state.trace.cm_write).record(row, state.trace.accepting);
}
void publish(const std::shared_ptr<Publishers> & pubs,
  const SnapshotLease & lease, SensorWorker & owner)
{
  const auto sample = read_native(owner.model(), lease.data(), lease.epoch());
  if (!std::isfinite(sample.stamp) || sample.stamp < 0.) {
    throw std::invalid_argument("invalid native capture time");
  }
  const builtin_interfaces::msg::Time stamp =
    rclcpp::Time(static_cast<int64_t>(std::llround(sample.stamp*1e9)));
  integrated_robot_interfaces::msg::FootContacts feet;
  feet.header.frame_id = "odom"; feet.header.stamp = stamp;
  feet.epoch = lease.epoch(); feet.sequence = lease.sequence();
  feet.unexpected_contacts = sample.unexpected_contacts;
  for (size_t i = 0; i < 4; ++i) {
    feet.names[i] = sample.feet[i].name;
    feet.points[i].x = sample.feet[i].point[0];
    feet.points[i].y = sample.feet[i].point[1];
    feet.points[i].z = sample.feet[i].point[2];
    feet.normal_forces[i] = sample.feet[i].normal_force;
    feet.touching[i] = sample.feet[i].touching;
  }
  sensor_msgs::msg::Imu imu;
  imu.header.stamp = stamp; imu.header.frame_id = "base_link";
  imu.orientation_covariance[0] = -1.;  // orientation is not estimated by this sensor
  imu.linear_acceleration.x = sample.acceleration[0];
  imu.linear_acceleration.y = sample.acceleration[1];
  imu.linear_acceleration.z = sample.acceleration[2];
  imu.angular_velocity.x = sample.angular_velocity[0];
  imu.angular_velocity.y = sample.angular_velocity[1];
  imu.angular_velocity.z = sample.angular_velocity[2];
  geometry_msgs::msg::PoseStamped com;
  com.header = feet.header;
  com.pose.position.x = sample.center_of_mass[0];
  com.pose.position.y = sample.center_of_mass[1];
  com.pose.position.z = sample.center_of_mass[2];
  com.pose.orientation.w = 1.;  // position is a point, not a robot/TF pose
  nlohmann::json actuators = nlohmann::json::array();
  for (const auto & value : read_native_controls(owner.model(), lease.data())) {
    actuators.push_back({{"actuator_id", value.actuator_id}, {"ctrl_index", value.ctrl_index},
      {"output_index", value.output_index}, {"joint_name", value.joint_name},
      {"joint_type", value.joint_type}, {"control_kind", value.control_kind},
      {"position", value.position}, {"velocity", value.velocity}, {"ctrl", value.ctrl},
      {"actuator_force", value.actuator_force}, {"joint_force", value.joint_force},
      {"kp", value.kp}, {"kv", value.kv}, {"gear", value.gear},
      {"force_limited", value.force_limited}, {"ctrl_limited", value.ctrl_limited},
      {"force_range", value.force_range}, {"ctrl_range", value.ctrl_range}});
  }
  std_msgs::msg::String controls;
  controls.data = nlohmann::json{{"schema", 1},
    {"capture_ns", static_cast<int64_t>(std::llround(sample.stamp*1e9))},
    {"epoch", lease.epoch()}, {"sequence", lease.sequence()}, {"actuators", actuators},
    {"body_reference", {{"frame_id", "base_link"}, {"source", "mujoco_free_joint_qvel"},
      {"angular_velocity", sample.body_angular_velocity}}}}.dump();
  sensor_msgs::msg::LaserScan scan;
  const bool scan_due = sample.stamp-pubs->last_scan >= .1-1e-9;
  if (scan_due) {
    scan.header.stamp = stamp; scan.header.frame_id = "lidar_link";
    constexpr double pi = 3.14159265358979323846;
    scan.angle_min = -pi; scan.angle_increment = 2.*pi/360.;
    scan.angle_max = -pi + 359.*2.*pi/360.;
    scan.range_min = .05; scan.range_max = 10.; scan.scan_time = .1;
    // All rays belong to this native snapshot, not a rolling acquisition.
    const auto ranges = cast_scan(owner.model(), lease.data());
    scan.ranges.assign(ranges.begin(), ranges.end());
  }
  owner.publish_if_current(lease, [&] {
    pubs->feet->publish(feet); pubs->imu->publish(imu); pubs->com->publish(com);
    pubs->controls->publish(controls);
    if (scan_due) {pubs->scan->publish(scan); pubs->last_scan = sample.stamp;}
  });
}
}

class NativeNavigationSensorsPlugin
  : public mujoco_ros2_control_plugins::MuJoCoROS2ControlPluginBase
{
public:
  ~NativeNavigationSensorsPlugin() override {cleanup();}
  bool init(rclcpp::Node::SharedPtr node, const mjModel * model, mjData * data) override
  {
    cleanup();
    if (!node || !model || !data) {return false;}
    try {
      read_native(model, data, 0);  // fail initialization for missing native entities
      auto state = std::make_shared<PluginState>();
      for (const auto & actuator : read_native_controls(model, data)) {
        const auto joint = mj_name2id(model, mjOBJ_JOINT, actuator.joint_name.c_str());
        state->trace_names.push_back(actuator.joint_name);
        state->trace_ctrl_indices.push_back(actuator.ctrl_index);
        state->trace_dof_indices.push_back(model->jnt_dofadr[joint]);
      }
      if (state->trace_names.size() > 64 || model->nv < 6 || model->njnt < 1 ||
        model->jnt_type[0] != mjJNT_FREE || model->jnt_dofadr[0] != 0) {
        throw std::invalid_argument("unsupported command trace dimensions");
      }
      auto pubs = std::make_shared<Publishers>();
      auto applied = node->create_publisher<sensor_msgs::msg::JointState>(
        "/navigation/applied_reference",rclcpp::QoS(rclcpp::KeepLast(1)).reliable());
      const auto names=state->trace_names;
      state->applied_worker=std::make_shared<AppliedReferenceWorker>(names.size(),
        [applied,names](const AppliedReferenceRow & row) {
          sensor_msgs::msg::JointState msg;
          msg.header.stamp=rclcpp::Time(row.stamp_ns);msg.header.frame_id="mujoco/pre_step";
          msg.name=names;msg.position.assign(row.values.begin(),row.values.begin()+names.size());
          applied->publish(msg);
        });
      const auto qos = rclcpp::SensorDataQoS();
      pubs->feet = node->create_publisher<integrated_robot_interfaces::msg::FootContacts>(
        "/navigation/foot_contacts", qos);
      pubs->imu = node->create_publisher<sensor_msgs::msg::Imu>("/navigation/imu", qos);
      pubs->scan = node->create_publisher<sensor_msgs::msg::LaserScan>("/scan", qos);
      pubs->com = node->create_publisher<geometry_msgs::msg::PoseStamped>("/navigation/native_com", qos);
      pubs->controls = node->create_publisher<std_msgs::msg::String>(
        "/navigation/native_controls", rclcpp::QoS(rclcpp::KeepLast(100)).reliable());
      state->worker = std::make_shared<SensorWorker>(model,
        [pubs](const SnapshotLease & lease, SensorWorker & owner) {publish(pubs, lease, owner);});
      const std::weak_ptr<PluginState> weak = state;
      state->trace_service = node->create_service<std_srvs::srv::Trigger>(
        "/navigation/native_command_trace",
        [weak](std_srvs::srv::Trigger::Request::SharedPtr,
          std_srvs::srv::Trigger::Response::SharedPtr response) {
          if (auto current = weak.lock()) {
            current->trace.stop();
            response->message = nlohmann::json{{"schema", 1}, {"frozen", true},
              {"invalid_time", current->trace.invalid_time.load()},
              {"joints", current->trace_names},
              {"cm_write_scope", "staged_ctrl_with_older_snapshot_not_physics_apply"},
              {"pre_step_scope", "applied_ctrl_before_next_mj_step_and_previous_step_velocity"},
              {"cm_write", current->trace.cm_write.export_frozen(current->trace_names.size(), 2000)},
              {"pre_step", current->trace.pre_step.export_frozen(current->trace_names.size(), 6000)}}.dump();
            response->success = true;
          }
        });
      state->stop_service = node->create_service<std_srvs::srv::Trigger>(
        "/navigation/stop_native_sensors",
        [weak](std_srvs::srv::Trigger::Request::SharedPtr,
          std_srvs::srv::Trigger::Response::SharedPtr response) {
          if (auto current = weak.lock()) {
            {
              std::lock_guard<std::mutex> lock(current->mutex);
              current->stopped = true; current->reason = "requested_stop";
            }
            current->worker->stop();
            current->applied_worker->stop();
            response->success = !current->worker->failed() && !current->applied_worker->failed();
            response->message = nlohmann::json{{"sensor_worker_joined",true},
              {"engine_exit_acknowledgment",false},
              {"applied_worker_joined",current->applied_worker->joined()},
              {"applied_submitted",current->applied_worker->submitted()},
              {"applied_published",current->applied_worker->published()},
              {"applied_dropped_busy",current->applied_worker->dropped_busy()},
              {"applied_overwritten",current->applied_worker->overwritten()}}.dump();
          }
        });
      state->health_service = node->create_service<std_srvs::srv::Trigger>(
        "/navigation/native_sensors_health",
        [weak](std_srvs::srv::Trigger::Request::SharedPtr,
          std_srvs::srv::Trigger::Response::SharedPtr response) {
          if (auto current = weak.lock()) {
            std::lock_guard<std::mutex> lock(current->mutex);
            response->success = !current->stopped && !current->worker->failed()
              && !current->applied_worker->failed();
            response->message = current->reason + ";capture=" + std::to_string(current->last_submitted);
          }
        });
      std::atomic_store(&state_, state);
      RCLCPP_INFO(node->get_logger(), "native navigation sensor MuJoCo header=%d library=%d (%s)",
        mjVERSION_HEADER, mj_version(), mj_versionString());
      return true;
    } catch (const std::exception & error) {
      RCLCPP_ERROR(node->get_logger(), "native navigation sensor init failed: %s", error.what());
      cleanup(); return false;
    }
  }
  void update(const mjModel * model, mjData * data) override
  {
    auto state = std::atomic_load(&state_);
    if (!state || !data) {return;}
    trace_numeric(*state, data, false);
    std::lock_guard<std::mutex> lock(state->mutex);
    if (state->stopped) {return;}
    if (!std::isfinite(data->time) || data->time < state->last_observed) {
      state->stopped = true; state->reason = "clock_rollback_or_invalid;restart_required";
      state->worker->request_stop(); return;
    }
    state->last_observed = data->time;
    if (data->time-state->last_submitted < .02-1e-9) {return;}
    try {
      if (state->worker->submit(model, data)) {state->last_submitted = data->time;}
    } catch (const std::exception & error) {
      state->stopped = true; state->reason = error.what(); state->worker->request_stop();
    }
  }
  void pre_step(mjData * data) override
  {
    auto state = std::atomic_load(&state_);
    if (state && data) {
      trace_numeric(*state, data, true);
      if(std::isfinite(data->time) && data->time>=0.) {
        AppliedReferenceRow row;
        // Serialize this SAME pre_step capture as the fixed engine /clock does.
        // No later clock read, future tolerance or timestamp renewal is used.
        const auto capture_sec=static_cast<int32_t>(std::floor(data->time));
        const auto capture_nsec=static_cast<uint32_t>((data->time-capture_sec)*1e9);
        row.stamp_ns=static_cast<int64_t>(capture_sec)*1000000000LL+capture_nsec;
        for(size_t i=0;i<state->trace_ctrl_indices.size();++i) {
          row.values[i]=data->ctrl[state->trace_ctrl_indices[i]];
        }
        state->applied_worker->submit(row);
      } else {state->applied_worker->fail();}
    }
  }
  void on_reset(mjData *) override
  {
    if (auto state = std::atomic_load(&state_)) {
      state->trace.stop();
      std::lock_guard<std::mutex> lock(state->mutex);
      state->stopped = true; state->reason = "world_reset;restart_required";
      state->worker->request_stop();  // no joining on the physics thread
      state->applied_worker->request_stop();
    }
  }
  void cleanup() override
  {
    auto state = std::atomic_exchange(&state_, std::shared_ptr<PluginState>{});
    if (state) {
      state->trace.stop();
      {std::lock_guard<std::mutex> lock(state->mutex); state->stopped = true;}
      state->worker->stop();
      state->applied_worker->stop();
    }
  }
private:
  std::shared_ptr<PluginState> state_;
};
}  // namespace integrated_robot_navigation_sensors

PLUGINLIB_EXPORT_CLASS(integrated_robot_navigation_sensors::NativeNavigationSensorsPlugin,
  mujoco_ros2_control_plugins::MuJoCoROS2ControlPluginBase)
