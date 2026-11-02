// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include "integrated_robot_navigation_sensors/command_trace.hpp"
#include "integrated_robot_navigation_sensors/applied_reference.hpp"
#include <chrono>
#include <condition_variable>
#include <limits>
namespace nav = integrated_robot_navigation_sensors;

TEST(AppliedReference, ReadOnlyCopyPermanentStopAndNormalJoin)
{
  std::mutex mutex;std::condition_variable wake;
  std::vector<nav::AppliedReferenceRow> rows;
  nav::AppliedReferenceWorker worker(1,[&](const auto & row) {
    std::lock_guard<std::mutex> lock(mutex);rows.push_back(row);wake.notify_one();
  });
  nav::AppliedReferenceRow input;input.stamp_ns=20;input.values[0]=.789;
  worker.submit(input);input.values[0]=.999;
  {std::unique_lock<std::mutex> lock(mutex);
    ASSERT_TRUE(wake.wait_for(lock,std::chrono::seconds(1),[&] {return !rows.empty();}));}
  worker.stop();worker.submit(input);worker.stop();
  ASSERT_EQ(rows.size(),1u);EXPECT_DOUBLE_EQ(rows[0].values[0],.789);
  EXPECT_EQ(rows[0].stamp_ns,20);EXPECT_TRUE(worker.joined());EXPECT_FALSE(worker.failed());
  EXPECT_EQ(worker.submitted(),1u);EXPECT_EQ(worker.published(),1u);
}

TEST(AppliedReference, CallbackFailureCannotRestartAndInvalidNumbersFailClosed)
{
  nav::AppliedReferenceWorker worker(1,[](const auto &) {throw std::runtime_error("publisher");});
  nav::AppliedReferenceRow row;row.stamp_ns=20;worker.submit(row);worker.stop();
  EXPECT_TRUE(worker.failed());EXPECT_TRUE(worker.joined());EXPECT_EQ(worker.published(),0u);
  row.stamp_ns=40;worker.submit(row);EXPECT_EQ(worker.submitted(),1u);
  nav::AppliedReferenceWorker invalid(1,[](const auto &) {});
  row.values[0]=std::numeric_limits<double>::quiet_NaN();invalid.submit(row);invalid.stop();
  EXPECT_TRUE(invalid.failed());EXPECT_EQ(invalid.submitted(),0u);
}

TEST(CommandTrace, BoundedOverwriteAndExportOmissionAreExplicit)
{
  nav::CommandTraceLane lane(3);
  std::atomic<bool> accepting{true};
  for (int i=1; i<=5; ++i) {
    nav::CommandTraceRow row;
    row.snapshot_ros_ns=i*2000000; row.steady_ns=i*3000000; row.ctrl[0]=i;
    lane.record(row, accepting);
  }
  accepting=false;
  auto result=lane.export_frozen(1, 2);
  EXPECT_EQ(result.at("total"), 5);
  EXPECT_EQ(result.at("capacity"), 3);
  EXPECT_EQ(result.at("overwritten"), 2);
  EXPECT_EQ(result.at("omitted_from_export"), 1);
  EXPECT_EQ(result.at("dropped_busy"), 0);
  EXPECT_EQ(result.at("rows")[0].at("sequence"), 4);
  EXPECT_DOUBLE_EQ(result.at("rows")[1].at("ctrl")[0].get<double>(), 5.);
}

TEST(CommandTrace, StopIsPermanentAndInputStorageIsNeverAliased)
{
  nav::NativeCommandTrace trace;
  nav::CommandTraceRow row;
  row.ctrl[0]=.123;
  trace.cm_write.record(row, trace.accepting);
  row.ctrl[0]=.456;
  trace.stop();
  trace.cm_write.record(row, trace.accepting);
  trace.pre_step.record(row, trace.accepting);
  auto cm=trace.cm_write.export_frozen(1, 20);
  EXPECT_EQ(cm.at("total"), 1);
  EXPECT_DOUBLE_EQ(cm.at("rows")[0].at("ctrl")[0].get<double>(), .123);
  EXPECT_EQ(trace.pre_step.export_frozen(1, 20).at("total"), 0);
  EXPECT_EQ(trace.cm_write.export_frozen(1, 20), cm);
}
