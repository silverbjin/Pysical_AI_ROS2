// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <mujoco/mujoco.h>
#include <array>
#include <cstdint>
#include <string>

namespace integrated_robot_navigation_sensors
{
struct FootSample
{
  std::string name;
  std::array<double, 3> point{};
  double normal_force{0};
  bool touching{false};
};
struct NavigationSample
{
  uint64_t epoch{0};
  double stamp{0};
  std::array<FootSample, 4> feet;
  std::array<double, 3> acceleration{}, angular_velocity{}, center_of_mass{};
  uint32_t unexpected_contacts{0};
};
std::array<double, 3> contact_world_force(const std::array<double, 9> & frame,
  const std::array<double, 3> & force, int side);
NavigationSample read_native(const mjModel *, const mjData *, uint64_t epoch);
std::array<float, 360> cast_scan(const mjModel *, const mjData *);
}  // namespace integrated_robot_navigation_sensors
