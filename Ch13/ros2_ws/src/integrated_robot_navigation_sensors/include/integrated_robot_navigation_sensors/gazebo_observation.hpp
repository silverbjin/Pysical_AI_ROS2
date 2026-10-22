// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <chrono>
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
GazeboObservation read_gazebo_observations(gz::sim::Entity model,
  const gz::sim::EntityComponentManager &, std::chrono::steady_clock::duration stamp);
}  // namespace integrated_robot_navigation_sensors
