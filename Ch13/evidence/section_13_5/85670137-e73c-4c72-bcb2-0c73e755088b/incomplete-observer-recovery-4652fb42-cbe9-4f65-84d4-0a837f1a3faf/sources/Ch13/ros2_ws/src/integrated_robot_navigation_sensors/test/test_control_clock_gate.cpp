// SPDX-License-Identifier: Apache-2.0
// Breaks caught: fabricated time, unbounded forwarding, duplicate lease renewal,
// replacement authority, clock rollback and publication after close/fault.
#include <gtest/gtest.h>
#include "integrated_robot_navigation_sensors/control_clock_gate.hpp"
using integrated_robot_navigation_sensors::ControlClockGate;

TEST(ControlClockGate, BootstrapGapDoesNotPretendControlHasAlreadyActivated)
{
  ControlClockGate gate;
  gate.receive(4000000, 1000000000, "a");
  ASSERT_EQ(gate.poll(1000000000, 1, 1).value(), 4000000);
  EXPECT_FALSE(gate.poll(1300000000, 1, 1));  // bootstrap, no invented clock
  EXPECT_TRUE(gate.fault().empty());  // no motor activation or progress lease yet
  gate.receive(8000000, 1400000000, "a");
  ASSERT_TRUE(gate.poll(1400000000, 1, 1));
}

TEST(ControlClockGate, OriginalValuesOnlyAndAtMost100Hz)
{
  ControlClockGate gate;
  gate.receive(1234567890, 1000000000, "owner-a");
  ASSERT_EQ(gate.poll(1000000000, 1, 1).value(), 1234567890);
  gate.receive(1236567890, 1002000000, "owner-a");
  EXPECT_FALSE(gate.poll(1009999999, 1, 1));
  EXPECT_EQ(gate.poll(1010000000, 1, 1).value(), 1236567890);
  EXPECT_FALSE(gate.poll(1020000000, 1, 1));  // no invented intermediate time
}

TEST(ControlClockGate, DuplicateInputCannotRenewProgressLeaseOrRepublish)
{
  ControlClockGate gate;
  gate.receive(10, 1000000000, "a");
  ASSERT_TRUE(gate.arm(1000000000));
  ASSERT_TRUE(gate.poll(1000000000, 1, 1));
  gate.receive(10, 1199999999, "a");
  EXPECT_FALSE(gate.poll(1200000001, 1, 1));
  EXPECT_EQ(gate.fault(), "source_stalled");
  gate.receive(11, 1200000002, "a");
  EXPECT_FALSE(gate.poll(1210000000, 1, 1));  // no automatic recovery
}

TEST(ControlClockGate, PauseBeforeFirstPositiveStampDoesNotInventTime)
{
  ControlClockGate gate;
  EXPECT_FALSE(gate.poll(1000000000, 0, 1));
  gate.receive(0, 1100000000, "a");
  EXPECT_EQ(gate.poll(1100000000, 1, 1).value(), 0);
  EXPECT_FALSE(gate.poll(2000000000, 1, 1));
  EXPECT_TRUE(gate.fault().empty());
  gate.receive(2, 2000000000, "a");
  EXPECT_EQ(gate.poll(2000000000, 1, 1).value(), 2);
}

TEST(ControlClockGate, RollbackAndAuthorityChangeAreSticky)
{
  for (bool replace : {false, true}) {
    ControlClockGate gate;
    gate.receive(100, 1000000000, "a");
    gate.receive(replace ? 101 : 99, 1001000000, replace ? "b" : "a");
    EXPECT_EQ(gate.fault(), replace ? "source_changed" : "source_rollback");
    gate.receive(102, 1002000000, "a");
    EXPECT_FALSE(gate.poll(1010000000, 1, 1));
  }
}

TEST(ControlClockGate, MissingMultipleOrCompetingPublishersFailClosed)
{
  for (const auto & counts : {std::pair<int,int>{0,1}, {2,1}, {1,2}, {1,0}}) {
    ControlClockGate gate;
    gate.receive(100, 1000000000, "a");
    EXPECT_FALSE(gate.poll(1000000000, counts.first, counts.second));
    EXPECT_FALSE(gate.fault().empty());
    EXPECT_FALSE(gate.poll(1010000000, 1, 1));
  }
}

TEST(ControlClockGate, InvalidStampIdentityAndWallRollbackFailClosed)
{
  ControlClockGate negative;
  negative.receive(-1, 1000000000, "a");
  EXPECT_EQ(negative.fault(), "invalid_stamp");
  ControlClockGate missing;
  missing.receive(1, 1000000000, "");
  EXPECT_EQ(missing.fault(), "invalid_gid");
  ControlClockGate wall;
  wall.receive(1, 1000000000, "a");
  EXPECT_FALSE(wall.poll(999999999, 1, 1));
  EXPECT_EQ(wall.fault(), "wall_rollback");
}

TEST(ControlClockGate, LateNewInputCannotHideExpiredProgressLease)
{
  ControlClockGate gate;
  gate.receive(1, 1000000000, "a");
  ASSERT_TRUE(gate.arm(1000000000));
  gate.receive(2, 1200000001, "a");
  EXPECT_EQ(gate.fault(), "source_stalled");
  EXPECT_FALSE(gate.poll(1210000000, 1, 1));
}

TEST(ControlClockGate, StaleBootstrapCannotBeArmedOrRepublishedAndNoArmRecovery)
{
  ControlClockGate gate;
  gate.receive(1, 1000000000, "a");
  EXPECT_FALSE(gate.poll(1200000001, 1, 1));  // pending stale input not yet published
  EXPECT_FALSE(gate.arm(1200000001));
  EXPECT_EQ(gate.fault(), "arming_requires_fresh_positive_clock");
  gate.receive(2, 1200000002, "a");
  EXPECT_FALSE(gate.arm(1200000003));
  EXPECT_FALSE(gate.armed());
}

TEST(ControlClockGate, CloseBlocksOutstandingAndFutureInputs)
{
  ControlClockGate gate;
  gate.receive(1, 1000000000, "a");
  gate.close();
  EXPECT_FALSE(gate.poll(1000000000, 1, 1));
  gate.receive(2, 1010000000, "a");
  EXPECT_FALSE(gate.poll(1010000000, 1, 1));
  EXPECT_TRUE(gate.closing());
}
