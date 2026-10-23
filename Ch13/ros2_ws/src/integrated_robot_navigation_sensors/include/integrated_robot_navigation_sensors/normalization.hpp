// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <mujoco/mujoco.h>
#include <array>
#include <cstdint>
#include <string>
#include <vector>

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
  std::array<double, 3> body_angular_velocity{};  // independent free-joint qvel, not gyro
  uint32_t unexpected_contacts{0};
};
struct ActuatorSample
{
  int actuator_id{0}, ctrl_index{0}, output_index{0};
  std::string joint_name, joint_type, control_kind;
  double position{0}, velocity{0}, ctrl{0}, actuator_force{0}, joint_force{0};
  double kp{0}, kv{0}, gear{0};
  bool force_limited{false}, ctrl_limited{false};
  std::array<double, 2> force_range{}, ctrl_range{};
};
std::array<double, 3> contact_world_force(const std::array<double, 9> & frame,
  const std::array<double, 3> & force, int side);
NavigationSample read_native(const mjModel *, const mjData *, uint64_t epoch);
std::vector<ActuatorSample> read_native_controls(const mjModel *, const mjData *);
std::array<float, 360> cast_scan(const mjModel *, const mjData *);
}  // namespace integrated_robot_navigation_sensors
