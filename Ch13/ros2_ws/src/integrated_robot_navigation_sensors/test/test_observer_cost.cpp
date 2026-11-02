// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include "integrated_robot_navigation_sensors/observer_cost.hpp"
using integrated_robot_navigation_sensors::ObserverCost;

TEST(ObserverCost, FixedStageCountersRetainActualWallAndCpuWithoutChangingCapture)
{
  ObserverCost cost;
  cost.add(ObserverCost::Update,100,160,20,35);
  cost.add(ObserverCost::Update,200,290,40,60);
  cost.add(ObserverCost::PostUpdate,300,350,80,90);
  cost.boundary(150,300);
  auto value=cost.report();
  const auto & stage=value.at("update");
  EXPECT_EQ(stage.at("calls"),2u);EXPECT_EQ(stage.at("wall_ns"),150);
  EXPECT_EQ(stage.at("cpu_ns"),35);EXPECT_EQ(stage.at("max_wall_ns"),90);
  EXPECT_EQ(value.at("post_update").at("calls"),1u);
  EXPECT_EQ(value.at("between_update_and_post").at("wall_ns"),150);
  EXPECT_EQ(value.at("scope"),"cumulative_owned_plugin_work_and_interphase_wall_not_physics_cpu");
  for(int i=0;i<10000;++i){cost.add(ObserverCost::Update,100,101,20,21);}
  EXPECT_EQ(cost.report().at("update").at("calls"),10002u);
  EXPECT_EQ(cost.report().size(),5u);  // no per-frame history allocation
}

TEST(ObserverCost, ActualScopeCompletesBeforeItsOriginalMutexOwnerCanPublish)
{
  ObserverCost cost;std::optional<int64_t> end;
  {ObserverCost::Scope measurement(cost,ObserverCost::Update,&end);EXPECT_GT(measurement.start_wall(),0);}
  ASSERT_TRUE(end);EXPECT_EQ(cost.report().at("update").at("calls"),1u);
  EXPECT_GT(cost.report().at("update").at("wall_ns"),0);
  EXPECT_EQ(cost.report().at("errors"),0u);
}

TEST(ObserverCost, InvalidIntervalsDoNotCreatePositivePerformanceEvidence)
{
  ObserverCost cost;
  EXPECT_THROW(cost.add(ObserverCost::Update,100,99,20,21),std::invalid_argument);
  EXPECT_THROW(cost.add(ObserverCost::Update,100,101,20,19),std::invalid_argument);
  EXPECT_THROW(cost.boundary(100,99),std::invalid_argument);
  EXPECT_EQ(cost.report().at("update").at("calls"),0u);
}
