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
// Empty until actual state and native command components are populated. No writes.
std::optional<gz::msgs::StringMsg> read_gazebo_controls(gz::sim::Entity model,
  const gz::sim::EntityComponentManager &, std::chrono::steady_clock::duration stamp,
  uint64_t sequence);
GazeboObservation read_gazebo_observations(gz::sim::Entity model,
  const gz::sim::EntityComponentManager &, std::chrono::steady_clock::duration stamp);
}  // namespace integrated_robot_navigation_sensors
