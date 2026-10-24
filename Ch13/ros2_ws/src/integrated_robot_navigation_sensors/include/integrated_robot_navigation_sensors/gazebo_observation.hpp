// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <chrono>
#include <optional>
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
