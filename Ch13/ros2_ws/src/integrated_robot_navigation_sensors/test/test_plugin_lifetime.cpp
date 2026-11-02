// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include <atomic>
#include <future>
#include "fixture.hpp"
#include "integrated_robot_navigation_sensors/snapshot.hpp"
using namespace std::chrono_literals;
namespace nav = integrated_robot_navigation_sensors;

TEST(WorkerLifetime, StopJoinsBeforeDestroyingModelOrLeasedData)
{
  auto model = nav_test::model();
  auto data = nav_test::settled(model.get());
  std::promise<void> entered, release;
  auto released = release.get_future().share();
  std::atomic<bool> read_valid{false};
  auto worker = std::make_unique<nav::SensorWorker>(
    model.get(), [&](const nav::SnapshotLease & lease, nav::SensorWorker & owner) {
      entered.set_value();
      released.wait();
      read_valid = owner.model()->nq > 0 && lease.data()->qpos[2] > .1;
    });
  ASSERT_TRUE(worker->submit(model.get(), data.get()));
  ASSERT_EQ(entered.get_future().wait_for(1s), std::future_status::ready);
  data.reset(); model.reset();  // worker owns its model and captured data
  auto stopped = std::async(std::launch::async, [&] {worker->stop();});
  EXPECT_EQ(stopped.wait_for(20ms), std::future_status::timeout);
  release.set_value();
  ASSERT_EQ(stopped.wait_for(1s), std::future_status::ready);
  stopped.get();
  EXPECT_TRUE(read_valid);
  worker.reset();
}

TEST(WorkerLifetime, StopInvalidatesAcquiredOldEpochBeforePublish)
{
  auto model = nav_test::model();
  auto data = nav_test::settled(model.get());
  std::promise<void> acquired, release;
  auto released = release.get_future().share();
  std::atomic<int> published{0};
  nav::SensorWorker worker(model.get(),
    [&](const nav::SnapshotLease & lease, nav::SensorWorker & owner) {
      acquired.set_value(); released.wait();
      owner.publish_if_current(lease, [&] {++published;});
    });
  ASSERT_TRUE(worker.submit(model.get(), data.get()));
  ASSERT_EQ(acquired.get_future().wait_for(1s), std::future_status::ready);
  worker.request_stop();
  release.set_value();
  worker.stop();
  EXPECT_EQ(published.load(), 0);
  EXPECT_FALSE(worker.failed());
}
