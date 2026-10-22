// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include <future>
#include "fixture.hpp"
#include "integrated_robot_navigation_sensors/snapshot.hpp"
using namespace std::chrono_literals;
namespace nav = integrated_robot_navigation_sensors;

TEST(Snapshot, PendingOverwriteDoesNotChangeHeldLease)
{
  auto model = nav_test::model();
  auto data = nav_test::settled(model.get());
  nav::SnapshotChannel channel(model.get());
  data->qpos[0] = 1.;
  ASSERT_TRUE(channel.submit(model.get(), data.get()));
  auto first = channel.wait_take();
  ASSERT_TRUE(first);
  data->time += .02; data->qpos[0] = 2.;
  ASSERT_TRUE(channel.submit(model.get(), data.get()));
  data->time += .02; data->qpos[0] = 3.;
  ASSERT_TRUE(channel.submit(model.get(), data.get()));
  EXPECT_DOUBLE_EQ(first->data()->qpos[0], 1.);
  first.reset();
  auto latest = channel.wait_take();
  ASSERT_TRUE(latest);
  EXPECT_DOUBLE_EQ(latest->data()->qpos[0], 3.);
  EXPECT_EQ(latest->sequence(), 3u);
  EXPECT_NE(channel.model(), model.get());
}

TEST(Snapshot, StopWakesWaiterAndRejectsFurtherSubmission)
{
  auto model = nav_test::model();
  auto data = nav_test::settled(model.get());
  nav::SnapshotChannel channel(model.get());
  auto waiter = std::async(std::launch::async, [&] {return channel.wait_take().has_value();});
  channel.request_stop();
  ASSERT_EQ(waiter.wait_for(1s), std::future_status::ready);
  EXPECT_FALSE(waiter.get());
  EXPECT_FALSE(channel.submit(model.get(), data.get()));
}
