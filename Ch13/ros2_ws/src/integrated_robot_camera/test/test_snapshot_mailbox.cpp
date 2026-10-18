// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include <mujoco/mujoco.h>

#include <chrono>
#include <future>
#include <limits>
#include <memory>
#include <set>
#include <stdexcept>
#include <utility>
#include <vector>

#include "integrated_robot_camera/snapshot_mailbox.hpp"

using integrated_robot_camera::SnapshotMailbox;
using namespace std::chrono_literals;

namespace
{
class MailboxTest : public ::testing::Test
{
protected:
  void SetUp() override
  {
    constexpr char xml[] = R"(<mujoco><worldbody>
      <camera name="first" pos="0 -2 1"/>
      <camera name="second" pos="0 2 1"/>
      <body><joint type="slide" axis="1 0 0"/>
      <geom type="sphere" size="0.1" mass="1"/></body>
      </worldbody></mujoco>)";
    mjVFS vfs;
    mj_defaultVFS(&vfs);
    ASSERT_EQ(mj_addBufferVFS(&vfs, "mailbox.xml", xml, sizeof(xml)), 0);
    char error[1024]{};
    model.reset(mj_loadXML("mailbox.xml", &vfs, error, sizeof(error)));
    mj_deleteVFS(&vfs);
    ASSERT_NE(model, nullptr) << error;
    input.reset(mj_makeData(model.get()));
    ASSERT_NE(input, nullptr);
  }

  void frame(double time, double x)
  {
    input->time = time;
    input->qpos[0] = x;
    mj_forward(model.get(), input.get());
  }

  bool send(SnapshotMailbox & mailbox, double time, double x,
    const std::vector<size_t> & cameras = {0})
  {
    frame(time, x);
    return mailbox.submit(model.get(), input.get(), cameras, mailbox.observe_time(time).epoch);
  }

  std::unique_ptr<mjModel, decltype(&mj_deleteModel)> model{nullptr, mj_deleteModel};
  std::unique_ptr<mjData, decltype(&mj_deleteData)> input{nullptr, mj_deleteData};
};

// A single shared rendering buffer would change the acquired frame here.
TEST_F(MailboxTest, ConsumerLeaseSurvivesProducerOverwrite)
{
  SnapshotMailbox mailbox(model.get(), 2);
  ASSERT_TRUE(send(mailbox, 1., 0.1));
  auto first = mailbox.wait_take();
  ASSERT_TRUE(first);
  const auto * captured_pointer = first->data();
  const double captured_x = first->data()->geom_xpos[0];
  EXPECT_DOUBLE_EQ(captured_x, 0.1);
  EXPECT_DOUBLE_EQ(first->stamp_seconds(), 1.);
  std::promise<void> release_producer;
  auto barrier = release_producer.get_future();
  auto producer = std::async(std::launch::async, [&] {
      barrier.wait();
      return send(mailbox, 2., 0.2, {1}) && send(mailbox, 3., 0.3, {1});
    });
  release_producer.set_value();
  ASSERT_EQ(producer.wait_for(2s), std::future_status::ready);
  EXPECT_TRUE(producer.get());  // producer completes while first lease is still held
  EXPECT_EQ(first->data(), captured_pointer);
  EXPECT_DOUBLE_EQ(first->data()->time, 1.);
  EXPECT_DOUBLE_EQ(first->data()->geom_xpos[0], captured_x);
  EXPECT_EQ(first->camera_indices(), (std::vector<size_t>{0}));
  const auto first_sequence = first->sequence();
  first.reset();
  auto latest = mailbox.wait_take();
  ASSERT_TRUE(latest);
  EXPECT_DOUBLE_EQ(latest->stamp_seconds(), 3.);
  EXPECT_DOUBLE_EQ(latest->data()->geom_xpos[0], 0.3);
  EXPECT_EQ(latest->camera_indices(), (std::vector<size_t>{1}));
  EXPECT_GT(latest->sequence(), first_sequence);
}

// Missing stop notification would leave the native worker blocked forever.
TEST_F(MailboxTest, StopWakesIdleConsumer)
{
  SnapshotMailbox mailbox(model.get(), 2);
  std::promise<void> entered;
  auto consumer = std::async(std::launch::async, [&] {
      entered.set_value();
      return mailbox.wait_take().has_value();
    });
  entered.get_future().wait();
  mailbox.request_stop();
  EXPECT_EQ(consumer.wait_for(2s), std::future_status::ready);
  EXPECT_FALSE(consumer.get());
  mailbox.request_stop();
}

TEST_F(MailboxTest, StopRejectsSubmitWhileLeaseRemainsValid)
{
  SnapshotMailbox mailbox(model.get(), 2);
  ASSERT_TRUE(send(mailbox, 1., 0.1));
  auto lease = mailbox.wait_take();
  ASSERT_TRUE(lease);
  mailbox.request_stop();
  EXPECT_FALSE(mailbox.is_current(lease->epoch()));
  EXPECT_FALSE(send(mailbox, 2., 0.2));
  EXPECT_DOUBLE_EQ(lease->data()->geom_xpos[0], 0.1);
  lease.reset();
  EXPECT_FALSE(mailbox.wait_take());
}

TEST_F(MailboxTest, RejectsSecondConsumerOrOutstandingLease)
{
  SnapshotMailbox mailbox(model.get(), 2);
  ASSERT_TRUE(send(mailbox, 1., 0.1));
  auto first = mailbox.wait_take();
  ASSERT_TRUE(first);
  EXPECT_THROW(mailbox.wait_take(), std::logic_error);
  auto second = std::async(std::launch::async, [&] {
      EXPECT_THROW(mailbox.wait_take(), std::logic_error);
    });
  second.get();
  // Moving must release exactly once, including move assignment to an engaged lease.
  auto moved = std::move(*first);
  first.reset();
  EXPECT_DOUBLE_EQ(moved.data()->time, 1.);
}

TEST_F(MailboxTest, RollbackDropsPendingAndInvalidatesOldLeaseEpoch)
{
  SnapshotMailbox mailbox(model.get(), 2);
  ASSERT_TRUE(send(mailbox, 3., 0.3));
  auto old = mailbox.wait_take();
  ASSERT_TRUE(old);
  ASSERT_TRUE(send(mailbox, 4., 0.4, {1}));
  const auto rewind = mailbox.observe_time(0.5);
  EXPECT_TRUE(rewind.rollback);
  EXPECT_NE(rewind.epoch, old->epoch());
  EXPECT_FALSE(mailbox.is_current(old->epoch()));
  EXPECT_DOUBLE_EQ(old->data()->time, 3.);
  old.reset();
  frame(0.5, 0.05);
  ASSERT_TRUE(mailbox.submit(model.get(), input.get(), {0}, rewind.epoch));
  auto fresh = mailbox.wait_take();
  ASSERT_TRUE(fresh);
  EXPECT_DOUBLE_EQ(fresh->stamp_seconds(), 0.5);
  EXPECT_EQ(fresh->epoch(), rewind.epoch);
}

TEST_F(MailboxTest, ResetBetweenObserveAndSubmitRejectsOldGeneration)
{
  SnapshotMailbox mailbox(model.get(), 2);
  const auto observed = mailbox.observe_time(1.);
  frame(1., 0.1);
  mailbox.reset_epoch();
  EXPECT_FALSE(mailbox.submit(model.get(), input.get(), {0}, observed.epoch));
  const auto next = mailbox.observe_time(0.);
  EXPECT_FALSE(next.rollback);
  EXPECT_NE(next.epoch, observed.epoch);
  EXPECT_TRUE(send(mailbox, 0., 0.));
}

TEST_F(MailboxTest, SameTimeDoesNotResetEpoch)
{
  SnapshotMailbox mailbox(model.get(), 2);
  auto observed = mailbox.observe_time(1.);
  auto same = mailbox.observe_time(1.);
  EXPECT_FALSE(same.rollback);
  EXPECT_EQ(same.epoch, observed.epoch);
  EXPECT_TRUE(mailbox.is_current(same.epoch));
}

TEST_F(MailboxTest, RejectsInvalidTimeAndCameraSelection)
{
  EXPECT_THROW(SnapshotMailbox(nullptr, 2), std::invalid_argument);
  SnapshotMailbox mailbox(model.get(), 2);
  for (double bad : {-1., std::numeric_limits<double>::infinity(),
    std::numeric_limits<double>::quiet_NaN()})
  {
    EXPECT_THROW(mailbox.observe_time(bad), std::invalid_argument);
    input->time = bad;
    EXPECT_THROW(mailbox.submit(model.get(), input.get(), {0}, 0), std::invalid_argument);
  }
  frame(1., 0.1);
  const auto epoch = mailbox.observe_time(1.).epoch;
  EXPECT_THROW(mailbox.submit(nullptr, input.get(), {0}, epoch), std::invalid_argument);
  EXPECT_THROW(mailbox.submit(model.get(), nullptr, {0}, epoch), std::invalid_argument);
  EXPECT_THROW(mailbox.submit(model.get(), input.get(), {2}, epoch), std::invalid_argument);
  EXPECT_THROW(mailbox.submit(model.get(), input.get(), {0, 0}, epoch), std::invalid_argument);
  EXPECT_TRUE(mailbox.submit(model.get(), input.get(), {0, 1}, epoch));
  auto both = mailbox.wait_take();
  ASSERT_TRUE(both);
  EXPECT_EQ(both->camera_indices(), (std::vector<size_t>{0, 1}));
}

TEST_F(MailboxTest, OnlyTwoDataBuffersAreReused)
{
  SnapshotMailbox mailbox(model.get(), 2);
  std::set<const mjData *> addresses;
  for (size_t i = 0; i < 100; ++i) {
    ASSERT_TRUE(send(mailbox, i, 0.001 * i));
    auto lease = mailbox.wait_take();
    ASSERT_TRUE(lease);
    addresses.insert(lease->data());
    EXPECT_NE(lease->data(), input.get());
  }
  EXPECT_EQ(addresses.size(), 2u);
}
}  // namespace
