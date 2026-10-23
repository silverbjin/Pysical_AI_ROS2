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
  const int root = m->body_jntadr[base];
  if (m->body_parentid[base] != 0 || m->body_jntnum[base] != 1 || root < 0 ||
    m->jnt_type[root] != mjJNT_FREE)
  {throw std::invalid_argument("native body gyro reference requires free root base_link");}
  const int angular = m->jnt_dofadr[root] + 3;
  if (angular < 3 || angular + 3 > m->nv) {
    throw std::invalid_argument("native free joint velocity address outside model");
  }
  // MuJoCo free-joint translation is WORLD, rotation is BODY. Do not rotate it
  // as world velocity, read sensordata again, or recompute/mutate this snapshot.
  std::copy_n(d->qvel + angular, 3, result.body_angular_velocity.begin());
  for (const auto value : result.body_angular_velocity) {
    if (!std::isfinite(value)) {throw std::invalid_argument("invalid native body angular velocity");}
  }
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

std::vector<ActuatorSample> read_native_controls(const mjModel * m, const mjData * d)
{
  if (!m || !d) {throw std::invalid_argument("native control model/data required");}
  std::vector<ActuatorSample> result;
#if mjVERSION_HEADER >= 3012000
  const int count = m->nactuator;
#else
  const int count = m->nu;
#endif
  result.reserve(count);
  for (int a = 0; a < count; ++a) {
    int ctrl = a, output = a;
#if mjVERSION_HEADER >= 3012000
    if (m->actuator_ctrlnum[a] != 1 || m->actuator_outnum[a] != 1) {
      throw std::invalid_argument("native observation requires scalar actuator input/output");
    }
    ctrl = m->actuator_ctrladr[a]; output = m->actuator_outadr[a];
    if (ctrl < 0 || ctrl >= m->nu || output < 0 || output >= m->nout) {
      throw std::invalid_argument("native actuator address outside model");
    }
#endif
    if (m->actuator_trntype[a] != mjTRN_JOINT) {
      throw std::invalid_argument("unsupported native actuator transmission");
    }
    const int joint = m->actuator_trnid[2*a];
    if (joint < 0 || joint >= m->njnt ||
      (m->jnt_type[joint] != mjJNT_HINGE && m->jnt_type[joint] != mjJNT_SLIDE))
    {throw std::invalid_argument("native actuator requires one scalar joint");}
    const auto * name = mj_id2name(m, mjOBJ_JOINT, joint);
    if (!name) {throw std::invalid_argument("native actuated joint must be named");}
    ActuatorSample sample;
    sample.actuator_id = a; sample.ctrl_index = ctrl; sample.output_index = output;
    sample.joint_name = name;
    sample.joint_type = m->jnt_type[joint] == mjJNT_HINGE ? "hinge" : "slide";
    sample.position = d->qpos[m->jnt_qposadr[joint]];
    sample.velocity = d->qvel[m->jnt_dofadr[joint]];
    sample.ctrl = d->ctrl[ctrl]; sample.actuator_force = d->actuator_force[output];
    sample.joint_force = d->qfrc_actuator[m->jnt_dofadr[joint]];
    sample.kp = m->actuator_gainprm[mjNGAIN*a];
    sample.kv = -m->actuator_biasprm[mjNBIAS*a+2];
    sample.gear = m->actuator_gear[6*output];  // installed mjmodel.h: (nout x 6)
    sample.control_kind = (m->actuator_gaintype[a] == mjGAIN_FIXED &&
      m->actuator_biastype[a] == mjBIAS_AFFINE && m->actuator_dyntype[a] == mjDYN_NONE &&
      sample.kp > 0. && sample.kv >= 0. &&
      std::abs(m->actuator_biasprm[mjNBIAS*a+1]+sample.kp) <= 1e-12*sample.kp) ?
      "position" : "other";
    sample.force_limited = m->actuator_forcelimited[a];
    sample.ctrl_limited = m->actuator_ctrllimited[ctrl];
    std::copy_n(m->actuator_forcerange+2*a, 2, sample.force_range.begin());
    std::copy_n(m->actuator_ctrlrange+2*ctrl, 2, sample.ctrl_range.begin());
    const std::array<double, 12> values{sample.position, sample.velocity, sample.ctrl,
      sample.actuator_force, sample.joint_force, sample.kp, sample.kv, sample.gear,
      sample.force_range[0], sample.force_range[1], sample.ctrl_range[0], sample.ctrl_range[1]};
    if (!std::all_of(values.begin(), values.end(), [](double value) {return std::isfinite(value);})) {
      throw std::invalid_argument("nonfinite native actuator observation");
    }
    result.push_back(sample);
  }
  return result;
}
}  // namespace integrated_robot_navigation_sensors
