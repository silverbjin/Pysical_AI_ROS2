// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <mujoco/mujoco.h>
#include <memory>
#include <stdexcept>
#include <string>

namespace nav_test
{
using Model = std::unique_ptr<mjModel, decltype(&mj_deleteModel)>;
using Data = std::unique_ptr<mjData, decltype(&mj_deleteData)>;
inline Model model()
{
  const char * xml = R"(
  <mujoco model="navigation_sensor_test">
    <option timestep=".002" gravity="0 0 -9.81" integrator="implicitfast"/>
    <default><geom group="1" friction="1 .005 .0001"/></default>
    <worldbody>
      <geom name="ground" type="plane" size="10 10 .1" group="0"/>
      <geom name="wall" type="box" pos="2 0 .3" size=".1 2 .3" group="0"/>
      <body name="base_link" pos="0 0 .15">
        <freejoint name="root"/>
        <geom name="base" type="box" size=".05 .05 .05" mass="1"/>
        <site name="navigation_imu_site" size=".001" rgba="0 0 0 0"/>
        <body name="lidar_link" pos="0 0 .2"/>
        <geom name="self_ray_blocker" type="box" pos=".3 0 .2" size=".02 .02 .02" mass="0"/>
        <body name="fr_foot" pos=".2 -.15 -.1"><geom name="fr_foot_collision" type="sphere" size=".05" mass=".1"/></body>
        <body name="fl_foot" pos=".2 .15 -.1"><geom name="fl_foot_collision" type="sphere" size=".05" mass=".1"/></body>
        <body name="rr_foot" pos="-.2 -.15 -.1"><geom name="rr_foot_collision" type="sphere" size=".05" mass=".1"/></body>
        <body name="rl_foot" pos="-.2 .15 -.1"><geom name="rl_foot_collision" type="sphere" size=".05" mass=".1"/></body>
        <body name="diagnostic_joint_body" pos="0 0 .1">
          <joint name="diagnostic_joint" axis="1 0 0" damping=".5"/>
          <geom type="sphere" size=".005" mass=".001"/>
        </body>
      </body>
    </worldbody>
    <actuator><motor joint="diagnostic_joint" ctrllimited="true" ctrlrange="-1 1"/></actuator>
    <sensor>
      <accelerometer name="navigation_accelerometer" site="navigation_imu_site"/>
      <gyro name="navigation_gyro" site="navigation_imu_site"/>
    </sensor>
  </mujoco>)";
  char error[1024]{};
  mjSpec * spec = mj_parseXMLString(xml, nullptr, error, sizeof(error));
  if (!spec) {throw std::runtime_error(error);}
  Model result(mj_compile(spec, nullptr), mj_deleteModel);
  const std::string detail = mjs_getError(spec);
  mj_deleteSpec(spec);
  if (!result) {throw std::runtime_error(detail);}
  return result;
}
inline Data settled(const mjModel * model)
{
  Data data(mj_makeData(model), mj_deleteData);
  for (int i = 0; i < 1000; ++i) {mj_step(model, data.get());}
  return data;
}
}  // namespace nav_test
