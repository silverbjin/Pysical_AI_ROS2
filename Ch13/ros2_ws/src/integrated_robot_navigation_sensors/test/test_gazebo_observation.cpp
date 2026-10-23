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
#include <gz/sim/components/JointAxis.hh>
#include <gz/sim/components/JointType.hh>
#include <gz/sim/components/JointPosition.hh>
#include <gz/sim/components/JointVelocity.hh>
#include <gz/sim/components/JointVelocityCmd.hh>
#include <gz/sim/components/JointTransmittedWrench.hh>
#include <nlohmann/json.hpp>
#include <gz/plugin/Loader.hh>
#include <gz/sim/System.hh>
#include "integrated_robot_navigation_sensors/gazebo_observation.hpp"
namespace sim = gz::sim;
namespace comp = gz::sim::components;
namespace nav = integrated_robot_navigation_sensors;

TEST(GazeboControls, NativePluginObservesCommandsBeforePhysicsClearsThem)
{
  gz::plugin::Loader loader;
  ASSERT_FALSE(loader.LoadLib(GZ_NAV_OBSERVER_LIBRARY).empty());
  auto plugin = loader.Instantiate("integrated_robot_navigation_sensors::GazeboObserver");
  ASSERT_TRUE(plugin);
  // All PreUpdates (including the real ros2_control write) precede Update.
  // Physics Update has default priority0 and consumes/clears the commands.
  ASSERT_NE(plugin->QueryInterface<sim::ISystemUpdate>(), nullptr);
  auto * priority = plugin->QueryInterface<sim::ISystemConfigurePriority>();
  ASSERT_NE(priority, nullptr);
  EXPECT_LT(priority->ConfigurePriority(), sim::System::kDefaultPriority);
}

TEST(GazeboControls, ActualScalarComponentsAndJointFrameEffortNotInferredTorque)
{
  sim::EntityComponentManager ecm;
  const auto robot = ecm.CreateEntity();
  ecm.CreateComponent(robot, comp::Model());
  const auto joint = ecm.CreateEntity();
  ecm.SetParentEntity(joint, robot);
  ecm.CreateComponent(joint, comp::ParentEntity(robot));
  ecm.CreateComponent(joint, comp::Name("fr_hip_joint"));
  ecm.CreateComponent(joint, comp::JointType(sdf::JointType::REVOLUTE));
  sdf::JointAxis axis;
  ASSERT_TRUE(axis.SetXyz(gz::math::Vector3d(0, 1, 0)).empty());
  axis.SetEffort(18.); axis.SetMaxVelocity(7.);
  axis.SetDamping(.35);
  axis.SetLower(-.8); axis.SetUpper(.8);
  ecm.CreateComponent(joint, comp::JointAxis(axis));
  // Before the real hardware exposes state/commands, no fabricated zero sample.
  EXPECT_FALSE(nav::read_gazebo_controls(robot, ecm, std::chrono::seconds(2), 3));
  ecm.CreateComponent(joint, comp::JointPosition({.12}));
  ecm.CreateComponent(joint, comp::JointVelocity({-.3}));
  ecm.CreateComponent(joint, comp::JointVelocityCmd({-.7}));
  gz::msgs::Wrench wrench;
  wrench.mutable_torque()->set_x(91.);
  wrench.mutable_torque()->set_y(-2.5);
  wrench.mutable_force()->set_y(123.);
  ecm.CreateComponent(joint, comp::JointTransmittedWrench(wrench));
  const auto observed = nav::read_gazebo_controls(robot, ecm, std::chrono::seconds(2), 3);
  ASSERT_TRUE(observed);
  const auto data = nlohmann::json::parse(observed->data());
  EXPECT_EQ(data.at("schema"), 2);
  EXPECT_EQ(data.at("engine"), "gazebo");
  EXPECT_EQ(data.at("capture_ns"), 2000000000);
  EXPECT_EQ(data.at("sequence"), 3);
  const auto & row = data.at("joints").at(0);
  EXPECT_EQ(row.at("name"), "fr_hip_joint");
  EXPECT_EQ(row.at("entity"), joint);
  EXPECT_EQ(row.at("position"), .12);
  EXPECT_EQ(row.at("velocity"), -.3);
  EXPECT_EQ(row.at("velocity_command"), -.7);
  EXPECT_EQ(row.at("projected_transmitted_effort"), -2.5);
  EXPECT_EQ(row.at("effort_unit"), "Nm");
  EXPECT_EQ(row.at("effort_limit"), 18.);
  EXPECT_EQ(row.at("native_damping"), .35);
  EXPECT_TRUE(row.at("applied_generalized_force").is_null());
  // Read-only observation must not clamp/replace actual native actuation.
  EXPECT_EQ(ecm.Component<comp::JointVelocityCmd>(joint)->Data().at(0), -.7);
  ecm.SetComponentData<comp::JointType>(joint, sdf::JointType::PRISMATIC);
  const auto prismatic = nlohmann::json::parse(
    nav::read_gazebo_controls(robot, ecm, std::chrono::seconds(3), 4)->data());
  EXPECT_EQ(prismatic.at("joints").at(0).at("projected_transmitted_effort"), 123.);
  EXPECT_EQ(prismatic.at("joints").at(0).at("effort_unit"), "N");
  ecm.SetComponentData<comp::JointVelocityCmd>(joint, {std::numeric_limits<double>::quiet_NaN()});
  EXPECT_THROW(nav::read_gazebo_controls(robot, ecm, std::chrono::seconds(4), 5), std::runtime_error);
}

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
