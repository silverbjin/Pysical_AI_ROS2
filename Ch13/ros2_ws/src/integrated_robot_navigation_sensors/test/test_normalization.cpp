// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include <cmath>
#include <vector>
#include "fixture.hpp"
#include "integrated_robot_navigation_sensors/normalization.hpp"
namespace nav = integrated_robot_navigation_sensors;

TEST(Normalization, ActualFootLoadsSumToWeightAndImuMeasuresGravity)
{
  auto model = nav_test::model();
  auto data = nav_test::settled(model.get());
  const auto sample = nav::read_native(model.get(), data.get(), 7);
  EXPECT_EQ(sample.epoch, 7u);
  EXPECT_NEAR(sample.stamp, 2., 1e-9);
  double total = 0.;
  const std::array<std::string, 4> names{"fr_foot", "fl_foot", "rr_foot", "rl_foot"};
  for (size_t i = 0; i < 4; ++i) {
    EXPECT_EQ(sample.feet[i].name, names[i]);
    EXPECT_GT(sample.feet[i].normal_force, 2.);
    EXPECT_TRUE(sample.feet[i].touching);
    EXPECT_NEAR(sample.feet[i].point[2], 0., .002);
    total += sample.feet[i].normal_force;
  }
  EXPECT_NEAR(total, 13.74381, .05);  // (1 + 4*.1 + .001) kg * 9.81
  EXPECT_NEAR(sample.acceleration[2], 9.81, .05);
  EXPECT_NEAR(sample.center_of_mass[2], .1215, .002);
  EXPECT_EQ(sample.unexpected_contacts, 0u);
}

TEST(Normalization, ReadingDoesNotWriteMotorOrPhysicsState)
{
  auto model = nav_test::model();
  auto data = nav_test::settled(model.get());
  data->ctrl[0] = .123;
  data->xfrc_applied[9] = .02;
  const std::vector<mjtNum> qpos(data->qpos, data->qpos + model->nq);
  const std::vector<mjtNum> qvel(data->qvel, data->qvel + model->nv);
  const std::vector<mjtNum> ctrl(data->ctrl, data->ctrl + model->nu);
  const std::vector<mjtNum> wrench(data->xfrc_applied, data->xfrc_applied + 6*model->nbody);
  nav::read_native(model.get(), data.get(), 0);
  nav::read_native_controls(model.get(), data.get());
  EXPECT_EQ(qpos, std::vector<mjtNum>(data->qpos, data->qpos + model->nq));
  EXPECT_EQ(qvel, std::vector<mjtNum>(data->qvel, data->qvel + model->nv));
  EXPECT_EQ(ctrl, std::vector<mjtNum>(data->ctrl, data->ctrl + model->nu));
  EXPECT_EQ(wrench, std::vector<mjtNum>(data->xfrc_applied, data->xfrc_applied + 6*model->nbody));
}

TEST(Normalization, BodyGyroReferenceReadsFreeJointNotSensorOrWorldVelocity)
{
  auto model = nav_test::model();
  auto data = nav_test::settled(model.get());
  // Rotate the body 90 degrees about z. Free-joint angular qvel is BODY frame.
  data->qpos[3] = std::sqrt(.5); data->qpos[4] = 0.;
  data->qpos[5] = 0.; data->qpos[6] = std::sqrt(.5);
  data->qvel[0] = 9.; data->qvel[1] = 8.; data->qvel[2] = 7.;
  data->qvel[3] = .1; data->qvel[4] = -.2; data->qvel[5] = .3;
  mj_forward(model.get(), data.get());
  const int gyro = mj_name2id(model.get(), mjOBJ_SENSOR, "navigation_gyro");
  data->sensordata[model->sensor_adr[gyro]] = 99.;  // cannot become ground truth
  const std::vector<mjtNum> before(data->qvel, data->qvel + model->nv);
  const auto sample = nav::read_native(model.get(), data.get(), 0);
  EXPECT_EQ(sample.body_angular_velocity, (std::array<double, 3>{.1, -.2, .3}));
  EXPECT_EQ(before, std::vector<mjtNum>(data->qvel, data->qvel + model->nv));
  EXPECT_DOUBLE_EQ(data->sensordata[model->sensor_adr[gyro]], 99.);
  model->jnt_type[0] = mjJNT_BALL;
  EXPECT_THROW(nav::read_native(model.get(), data.get(), 0), std::invalid_argument);
}

TEST(Normalization, ScanExcludesRobotButStillHitsWorldWall)
{
  auto model = nav_test::model();
  auto data = nav_test::settled(model.get());
  const auto scan = nav::cast_scan(model.get(), data.get());
  EXPECT_EQ(scan.size(), 360u);
  EXPECT_NEAR(scan[180], 1.9, .01);  // self box at .3m must not be returned
  EXPECT_TRUE(std::isinf(scan[0]));
}

TEST(Normalization, ContactForceAxesAndBodySideAreExplicit)
{
  const std::array<double, 9> frame{0, 0, 1, 1, 0, 0, 0, 1, 0};
  const std::array<double, 3> force{12, 0, 0};
  EXPECT_EQ(nav::contact_world_force(frame, force, 1), (std::array<double, 3>{0, 0, 12}));
  EXPECT_EQ(nav::contact_world_force(frame, force, -1), (std::array<double, 3>{0, 0, -12}));
}

TEST(Normalization, ActualActuatorControlIsNotInferredFromCommandTopics)
{
  auto model = nav_test::model();
  auto data = nav_test::settled(model.get());
  data->ctrl[0] = .37;
  mj_step(model.get(), data.get());
  const auto samples = nav::read_native_controls(model.get(), data.get());
  ASSERT_EQ(samples.size(), 1u);
  EXPECT_EQ(samples[0].joint_name, "diagnostic_joint");
  EXPECT_EQ(samples[0].joint_type, "hinge");
  EXPECT_EQ(samples[0].control_kind, "other");  // motor ctrl is effort, not a position target
  EXPECT_DOUBLE_EQ(samples[0].ctrl, .37);
  EXPECT_DOUBLE_EQ(samples[0].actuator_force, .37);
  EXPECT_DOUBLE_EQ(samples[0].position, data->qpos[model->jnt_qposadr[1]]);
  EXPECT_DOUBLE_EQ(samples[0].velocity, data->qvel[model->jnt_dofadr[1]]);
  model->actuator_biastype[0] = mjBIAS_AFFINE;
  model->actuator_gainprm[0] = 40.;
  model->actuator_biasprm[1] = -40.;
  model->actuator_biasprm[2] = -2.;
  const auto position = nav::read_native_controls(model.get(), data.get());
  EXPECT_EQ(position[0].control_kind, "position");
  EXPECT_DOUBLE_EQ(position[0].kp, 40.);
  EXPECT_DOUBLE_EQ(position[0].kv, 2.);
}

#if mjVERSION_HEADER >= 3012000
TEST(Normalization, MultiControlAddressIsRejectedBeforeReadingScalarArrays)
{
  auto model = nav_test::model();
  auto data = nav_test::settled(model.get());
  model->actuator_ctrlnum[0] = 2;
  EXPECT_THROW(nav::read_native_controls(model.get(), data.get()), std::invalid_argument);
  model->actuator_ctrlnum[0] = 1;
  model->actuator_outadr[0] = model->nout;
  EXPECT_THROW(nav::read_native_controls(model.get(), data.get()), std::invalid_argument);
  model->actuator_outadr[0] = 0;
}
#endif
