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
  EXPECT_EQ(qpos, std::vector<mjtNum>(data->qpos, data->qpos + model->nq));
  EXPECT_EQ(qvel, std::vector<mjtNum>(data->qvel, data->qvel + model->nv));
  EXPECT_EQ(ctrl, std::vector<mjtNum>(data->ctrl, data->ctrl + model->nu));
  EXPECT_EQ(wrench, std::vector<mjtNum>(data->xfrc_applied, data->xfrc_applied + 6*model->nbody));
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
