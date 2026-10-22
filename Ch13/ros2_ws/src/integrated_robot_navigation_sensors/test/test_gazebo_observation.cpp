// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/components/Collision.hh>
#include <gz/sim/components/ContactSensorData.hh>
#include <gz/sim/components/Inertial.hh>
#include <gz/sim/components/Link.hh>
#include <gz/sim/components/Model.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/components/Pose.hh>
#include <gz/sim/components/ParentEntity.hh>
#include <gz/sim/components/World.hh>
#include "integrated_robot_navigation_sensors/gazebo_observation.hpp"
namespace sim = gz::sim;
namespace comp = gz::sim::components;
namespace nav = integrated_robot_navigation_sensors;

TEST(GazeboObservation, NativeEcMassPoseFootNamesAndEmptyContactTick)
{
  sim::EntityComponentManager ecm;
  auto world = ecm.CreateEntity();
  ecm.CreateComponent(world, comp::World());
  ecm.CreateComponent(world, comp::Name("native_world"));
  ecm.CreateComponent(world, comp::Pose());
  auto robot = ecm.CreateEntity(); ecm.SetParentEntity(robot, world);
  ecm.CreateComponent(robot, comp::ParentEntity(world));
  ecm.CreateComponent(robot, comp::Model());
  ecm.CreateComponent(robot, comp::Name("integrated_robot"));
  ecm.CreateComponent(robot, comp::Pose(gz::math::Pose3d(1, 2, .5, 0, 0, 0)));
  const std::array<std::string, 4> feet{"fr_foot", "fl_foot", "rr_foot", "rl_foot"};
  std::vector<sim::Entity> collisions;
  for (size_t i = 0; i < feet.size(); ++i) {
    auto link = ecm.CreateEntity(); ecm.SetParentEntity(link, robot);
    ecm.CreateComponent(link, comp::ParentEntity(robot));
    ecm.CreateComponent(link, comp::Link());
    ecm.CreateComponent(link, comp::Name("native_link_"+std::to_string(i)));
    ecm.CreateComponent(link, comp::Pose(gz::math::Pose3d(0, 0, -.4, 0, 0, 0)));
    gz::math::Inertiald inertial;
    inertial.SetMassMatrix(gz::math::MassMatrix3d(1., gz::math::Vector3d(.1, .1, .1),
      gz::math::Vector3d::Zero));
    inertial.SetPose(gz::math::Pose3d(.1, 0, 0, 0, 0, 0));
    ecm.CreateComponent(link, comp::Inertial(inertial));
    auto collision = ecm.CreateEntity(); ecm.SetParentEntity(collision, link);
    ecm.CreateComponent(collision, comp::ParentEntity(link));
    ecm.CreateComponent(collision, comp::Collision());
    ecm.CreateComponent(collision, comp::Name("lumped__navcol__"+feet[i]+"__0"));
    ecm.CreateComponent(collision, comp::Pose());
    collisions.push_back(collision);
  }
  nav::request_gazebo_observations(robot, ecm);
  for (auto collision : collisions) {ASSERT_TRUE(ecm.Component<comp::ContactSensorData>(collision));}
  const auto result = nav::read_gazebo_observations(robot, ecm, std::chrono::seconds(3));
  EXPECT_NEAR(result.com.position().x(), 1.1, 1e-10);
  EXPECT_NEAR(result.com.position().y(), 2., 1e-10);
  EXPECT_NEAR(result.com.position().z(), .1, 1e-10);
  ASSERT_EQ(result.feet.pose_size(), 4);
  for (int i = 0; i < 4; ++i) {
    EXPECT_EQ(result.feet.pose(i).name(), feet[i]);
    EXPECT_NEAR(result.feet.pose(i).position().z(), .1, 1e-10);
  }
  EXPECT_EQ(result.contacts.contact_size(), 0);  // airborne ticks are observed too
  EXPECT_EQ(result.contacts.header().stamp().sec(), 3);
}
