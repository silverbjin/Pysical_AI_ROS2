// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <chrono>
#include <optional>
#include <nlohmann/json.hpp>
#include <gz/msgs/stringmsg.pb.h>
#include <gz/msgs/contacts.pb.h>
#include <gz/msgs/pose.pb.h>
#include <gz/msgs/pose_v.pb.h>
#include <gz/sim/EntityComponentManager.hh>

namespace integrated_robot_navigation_sensors
{
struct GazeboObservation
{
  gz::msgs::Pose com;
  gz::msgs::Pose_V feet;
  gz::msgs::Contacts contacts;
};
void request_gazebo_observations(gz::sim::Entity model, gz::sim::EntityComponentManager &);
// Owned value snapshots for the in-process observer. Same validation/schema
// as the legacy StringMsg wrappers below; no ECM references escape the call.
std::optional<nlohmann::json> read_gazebo_body_reference_json(gz::sim::Entity model,
  const gz::sim::EntityComponentManager &,std::chrono::steady_clock::duration,uint64_t sequence);
std::optional<nlohmann::json> read_gazebo_contact_reference_json(gz::sim::Entity model,
  const gz::sim::EntityComponentManager &,std::chrono::steady_clock::duration,
  bool compact_when_supported=false);
std::optional<nlohmann::json> read_gazebo_controls_json(gz::sim::Entity model,
  const gz::sim::EntityComponentManager &,std::chrono::steady_clock::duration,
  uint64_t sequence,bool require_commands=true);
// Independent completed-step body reference, never gyro/odometry/command data.
std::optional<gz::msgs::StringMsg> read_gazebo_body_reference(gz::sim::Entity model,
  const gz::sim::EntityComponentManager &, std::chrono::steady_clock::duration stamp,
  uint64_t sequence);
// Read-only raw completed-step foot contact diagnostics, not normalized support.
// Empty pairs remain empty even when a foot geometrically penetrates the floor.
std::optional<gz::msgs::StringMsg> read_gazebo_contact_reference(gz::sim::Entity model,
  const gz::sim::EntityComponentManager &, std::chrono::steady_clock::duration stamp,
  bool compact_when_supported = false);
// Default: actual state AND pre-step commands required. Debug post-step reads
// may explicitly allow cleared commands; missing commands stay null. No writes.
std::optional<gz::msgs::StringMsg> read_gazebo_controls(gz::sim::Entity model,
  const gz::sim::EntityComponentManager &, std::chrono::steady_clock::duration stamp,
  uint64_t sequence, bool require_commands = true);
GazeboObservation read_gazebo_observations(gz::sim::Entity model,
  const gz::sim::EntityComponentManager &, std::chrono::steady_clock::duration stamp);
}  // namespace integrated_robot_navigation_sensors
