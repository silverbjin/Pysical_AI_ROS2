// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/normalization.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace integrated_robot_navigation_sensors
{
namespace
{
int required(const mjModel * m, mjtObj type, const char * name)
{
  const int id = mj_name2id(m, type, name);
  if (id < 0) {throw std::invalid_argument(std::string("missing native sensor entity: ") + name);}
  return id;
}
std::array<double, 3> sensor3(const mjModel * m, const mjData * d, const char * name)
{
  const int id = required(m, mjOBJ_SENSOR, name);
  if (m->sensor_dim[id] != 3) {throw std::invalid_argument("native sensor must have 3 axes");}
  const auto * values = d->sensordata + m->sensor_adr[id];
  return {values[0], values[1], values[2]};
}
}
std::array<double, 3> contact_world_force(const std::array<double, 9> & frame,
  const std::array<double, 3> & force, int side)
{
  if (side != -1 && side != 1) {throw std::invalid_argument("contact side must be +/-1");}
  std::array<double, 3> world{};
  for (int i = 0; i < 3; ++i) {
    for (int j = 0; j < 3; ++j) {world[i] += side * frame[3*j+i] * force[j];}
  }
  return world;
}
NavigationSample read_native(const mjModel * m, const mjData * d, uint64_t epoch)
{
  NavigationSample result;
  result.epoch = epoch; result.stamp = d->time;
  const std::array<const char *, 4> names{"fr_foot", "fl_foot", "rr_foot", "rl_foot"};
  std::array<int, 4> feet;
  std::array<double, 4> weights{};
  for (size_t i = 0; i < 4; ++i) {
    feet[i] = required(m, mjOBJ_BODY, names[i]);
    result.feet[i].name = names[i];
    std::copy_n(d->xpos + 3*feet[i], 3, result.feet[i].point.begin());
  }
  const int ground = required(m, mjOBJ_GEOM, "ground");
  for (int c = 0; c < d->ncon; ++c) {
    const auto & contact = d->contact[c];
    if (contact.efc_address < 0 || contact.geom[0] < 0 || contact.geom[1] < 0) {continue;}
    int foot = -1, side = 0;
    for (size_t i = 0; i < feet.size(); ++i) {
      if (m->geom_bodyid[contact.geom[0]] == feet[i] && contact.geom[1] == ground) {
        foot = static_cast<int>(i); side = -1;
      } else if (m->geom_bodyid[contact.geom[1]] == feet[i] && contact.geom[0] == ground) {
        foot = static_cast<int>(i); side = 1;
      }
    }
    if (foot < 0) {++result.unexpected_contacts; continue;}
    mjtNum wrench[6]{};
    mj_contactForce(m, d, c, wrench);
    std::array<double, 9> frame;
    std::copy_n(contact.frame, 9, frame.begin());
    const auto world = contact_world_force(frame, {wrench[0], wrench[1], wrench[2]}, side);
    const double load = std::max(0., world[2]);  // world-z support, not norm of friction
    auto & target = result.feet[foot];
    if (weights[foot] == 0.) {target.point = {};}
    for (int j = 0; j < 3; ++j) {target.point[j] += load * contact.pos[j];}
    weights[foot] += load; target.normal_force += load;
    target.touching = target.normal_force >= 2.;
  }
  for (size_t i = 0; i < feet.size(); ++i) {
    if (weights[i] > 0.) {
      for (double & axis : result.feet[i].point) {axis /= weights[i];}
    }
  }
  result.acceleration = sensor3(m, d, "navigation_accelerometer");
  result.angular_velocity = sensor3(m, d, "navigation_gyro");
  const int base = required(m, mjOBJ_BODY, "base_link");
  std::copy_n(d->subtree_com + 3*base, 3, result.center_of_mass.begin());
  return result;
}
std::array<float, 360> cast_scan(const mjModel * m, const mjData * d)
{
  const int lidar = required(m, mjOBJ_BODY, "lidar_link");
  const mjtByte groups[6]{1, 0, 1, 1, 1, 1};  // only robot group 1 excluded
  std::array<float, 360> ranges;
  constexpr double pi = 3.14159265358979323846;
  for (size_t i = 0; i < ranges.size(); ++i) {
    const double theta = -pi + 2.*pi*i/ranges.size();
    const mjtNum local[3]{std::cos(theta), std::sin(theta), 0.};
    mjtNum ray[3];
    mju_mulMatVec3(ray, d->xmat + 9*lidar, local);
    int geom = -1;
    const double distance = mj_ray(m, d, d->xpos + 3*lidar, ray, groups, 1, -1, &geom
#if mjVERSION_HEADER >= 3012000
      , nullptr
#endif
    );
    ranges[i] = distance >= .05 && distance <= 10. ? static_cast<float>(distance) :
      std::numeric_limits<float>::infinity();
  }
  return ranges;
}
}  // namespace integrated_robot_navigation_sensors
