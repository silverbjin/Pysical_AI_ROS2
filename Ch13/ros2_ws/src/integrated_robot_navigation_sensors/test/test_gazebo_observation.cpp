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
#include <gz/sim/components/CanonicalLink.hh>
#include <gz/sim/components/AngularVelocity.hh>
#include <cmath>
#include <limits>
#include <nlohmann/json.hpp>
#include <gz/plugin/Loader.hh>
#include <gz/sim/System.hh>
#include "integrated_robot_navigation_sensors/gazebo_observation.hpp"
#include "integrated_robot_navigation_sensors/position_reference.hpp"
#include "integrated_robot_navigation_sensors/contact_detail_window.hpp"
#include "integrated_robot_navigation_sensors/dart_contact.hpp"
#include <dart/constraint/ContactConstraint.hpp>
namespace sim = gz::sim;
namespace comp = gz::sim::components;
namespace nav = integrated_robot_navigation_sensors;

TEST(GazeboBodyReference, InstantWorldVelocityRotatesToBodyWithoutReadingGyroOrWritingState)
{
  sim::EntityComponentManager ecm;
  const auto robot = ecm.CreateEntity();
  ecm.CreateComponent(robot,comp::Model());
  const auto link = ecm.CreateEntity();
  ecm.SetParentEntity(link,robot);
  ecm.CreateComponent(link,comp::ParentEntity(robot));
  ecm.CreateComponent(link,comp::Link());
  ecm.CreateComponent(link,comp::CanonicalLink());
  ecm.CreateComponent(link,comp::Name("base_footprint"));
  ecm.CreateComponent(link,comp::WorldPose(gz::math::Pose3d(1,2,3,0,0,M_PI_2)));
  EXPECT_FALSE(nav::read_gazebo_body_reference(robot,ecm,std::chrono::seconds(3),9));
  ecm.CreateComponent(link,comp::WorldAngularVelocity(gz::math::Vector3d(.2,.1,.3)));
  // Deliberately unrelated local/sensor value; reading it would make the test fail.
  ecm.CreateComponent(link,comp::AngularVelocity(gz::math::Vector3d(99,98,97)));
  const auto result = nav::read_gazebo_body_reference(robot,ecm,std::chrono::seconds(3),9);
  ASSERT_TRUE(result);
  const auto reference = nlohmann::json::parse(result->data());
  EXPECT_EQ(reference.at("capture_ns"),3000000000);
  EXPECT_EQ(reference.at("sequence"),9);
  EXPECT_EQ(reference.at("epoch"),0);
  EXPECT_EQ(reference.at("frame_id"),"base_footprint");
  EXPECT_EQ(reference.at("source"),"gazebo_ecm_world_angular_velocity");
  EXPECT_NEAR(reference.at("angular_velocity").at(0).get<double>(),.1,1e-12);
  EXPECT_NEAR(reference.at("angular_velocity").at(1).get<double>(),-.2,1e-12);
  EXPECT_NEAR(reference.at("angular_velocity").at(2).get<double>(),.3,1e-12);
  EXPECT_EQ(ecm.Component<comp::WorldAngularVelocity>(link)->Data(),gz::math::Vector3d(.2,.1,.3));
  EXPECT_EQ(ecm.Component<comp::AngularVelocity>(link)->Data(),gz::math::Vector3d(99,98,97));
  ecm.SetComponentData<comp::Name>(link,"different_base");
  EXPECT_THROW(nav::read_gazebo_body_reference(robot,ecm,std::chrono::seconds(3),9),std::runtime_error);
  ecm.SetComponentData<comp::Name>(link,"base_footprint");
  ecm.SetComponentData<comp::WorldAngularVelocity>(link,
    gz::math::Vector3d(std::numeric_limits<double>::quiet_NaN(),0,0));
  EXPECT_THROW(nav::read_gazebo_body_reference(robot,ecm,std::chrono::seconds(3),9),std::runtime_error);
}

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

TEST(G1DartContact, SingleWorldExplicitTransactionUsesActualGetterAndCannotBeClaimedTwice)
{
  using Contact=dart::constraint::ContactConstraint;
  struct Restore {double value;~Restore(){Contact::setErrorAllowance(value);}} restore{Contact::getErrorAllowance()};
  ASSERT_DOUBLE_EQ(restore.value,0.);
  for (double invalid : {0.,-.00005,.0001,std::numeric_limits<double>::quiet_NaN()}) {
    EXPECT_THROW(nav::configure_g1_dart_contact(invalid,1,true),std::runtime_error);
    EXPECT_DOUBLE_EQ(Contact::getErrorAllowance(),0.);
  }
  EXPECT_THROW(nav::configure_g1_dart_contact(.00005,2,true),std::runtime_error);
  EXPECT_THROW(nav::configure_g1_dart_contact(.00005,1,false),std::runtime_error);
  EXPECT_DOUBLE_EQ(Contact::getErrorAllowance(),0.);
  const auto report=nav::configure_g1_dart_contact(.00005,1,true);
  EXPECT_DOUBLE_EQ(report.before_m,0.);
  EXPECT_DOUBLE_EQ(report.effective_m,.00005);
  EXPECT_DOUBLE_EQ(Contact::getErrorAllowance(),.00005);
  EXPECT_FALSE(report.header_version.empty());
  EXPECT_NE(report.library_path.find("libdart.so."),std::string::npos);
  EXPECT_DOUBLE_EQ(nav::inspect_dart_contact().effective_m,.00005);
  // Test utility restores its process only; production has no reset/retry API.
  Contact::setErrorAllowance(0.);
  EXPECT_THROW(nav::configure_g1_dart_contact(.00005,1,true),std::runtime_error);
  EXPECT_DOUBLE_EQ(Contact::getErrorAllowance(),0.);
}

TEST(GazeboContactDiagnostic, OneFootLossOpensABoundedNativeWindowRatherThanHidingBehindTripodSupport)
{
  nav::ContactDetailWindow window;
  EXPECT_FALSE(window.observe(15));
  EXPECT_TRUE(window.observe(14));
  for (int i=0;i<9;++i) {EXPECT_TRUE(window.observe(14));}
  EXPECT_FALSE(window.observe(14));  // continuing airborne is not an unbounded verbose stream
  EXPECT_FALSE(window.observe(15)); // recovery alone does not renew the burst
  EXPECT_TRUE(window.observe(13));
  EXPECT_TRUE(window.observe(15));  // retain real following steps as well as the loss instant
  EXPECT_THROW(window.observe(16),std::runtime_error);
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
  EXPECT_FALSE(row.contains("position_reference"));
  ecm.CreateComponent(joint,nav::PositionReference({.14,.13,.02,2000000000.}));
  const auto reference=nlohmann::json::parse(
    nav::read_gazebo_controls(robot,ecm,std::chrono::seconds(2),3)->data()).at("joints").at(0).at("position_reference");
  EXPECT_EQ(reference.at("source_input"),.14);
  EXPECT_EQ(reference.at("applied"),.13);
  EXPECT_EQ(reference.at("ramp_s"),.02);
  EXPECT_EQ(reference.at("write_capture_ns"),2000000000);
  EXPECT_DOUBLE_EQ(ecm.Component<nav::PositionReference>(joint)->Data().at(1),.13);
  // Read-only observation must not clamp/replace actual native actuation.
  EXPECT_EQ(ecm.Component<comp::JointVelocityCmd>(joint)->Data().at(0), -.7);
  ecm.SetComponentData<comp::JointType>(joint, sdf::JointType::PRISMATIC);
  const auto prismatic = nlohmann::json::parse(
    nav::read_gazebo_controls(robot, ecm, std::chrono::seconds(3), 4)->data());
  EXPECT_EQ(prismatic.at("joints").at(0).at("projected_transmitted_effort"), 123.);
  EXPECT_EQ(prismatic.at("joints").at(0).at("effort_unit"), "N");
  // Physics may clear command components after consuming them. This state is
  // unavailable as pre-step command evidence, but valid post-step debug state.
  ecm.SetComponentData<comp::JointVelocityCmd>(joint, {});
  EXPECT_FALSE(nav::read_gazebo_controls(robot,ecm,std::chrono::seconds(3),4));
  const auto post=nav::read_gazebo_controls(robot,ecm,std::chrono::seconds(3),4,false);
  ASSERT_TRUE(post);
  const auto post_row=nlohmann::json::parse(post->data()).at("joints").at(0);
  EXPECT_TRUE(post_row.at("velocity_command").is_null());
  EXPECT_TRUE(post_row.at("force_command").is_null());
  EXPECT_EQ(post_row.at("position"),.12);
  EXPECT_EQ(post_row.at("velocity"),-.3);
  EXPECT_EQ(post_row.at("position_reference").at("write_capture_ns"),2000000000);
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
  // Preserve empty native ticks separately from geometric foot height. A low
  // foot center must NEVER be promoted to a measured contact/load.
  const auto empty = nlohmann::json::parse(nav::read_gazebo_contact_reference(
    robot,ecm,std::chrono::seconds(3))->data());
  EXPECT_EQ(empty.at("capture_ns"),3000000000);
  ASSERT_EQ(empty.at("feet").size(),4);
  EXPECT_EQ(empty.at("feet").at(0).at("pairs").size(),0);
  EXPECT_NEAR(empty.at("feet").at(0).at("center_world").at(2).get<double>(),.1,1e-10);
  gz::msgs::Contacts native;
  auto * pair = native.add_contact();
  pair->mutable_collision1()->set_id(collisions[0]);
  pair->mutable_collision2()->set_id(collisions[1]);
  pair->add_position()->set_z(.001);
  pair->add_depth(.0002);
  pair->add_wrench()->mutable_body_1_wrench()->mutable_force()->set_z(-12.);
  ecm.SetComponentData<comp::ContactSensorData>(collisions[0],native);
  const auto loaded = nlohmann::json::parse(nav::read_gazebo_contact_reference(
    robot,ecm,std::chrono::seconds(4))->data());
  const auto & raw = loaded.at("feet").at(0).at("pairs").at(0);
  EXPECT_EQ(loaded.at("capture_ns"),4000000000);
  EXPECT_EQ(raw.at("collision1_id"),collisions[0]);
  EXPECT_EQ(raw.at("collision2_id"),collisions[1]);
  EXPECT_EQ(raw.at("depths").at(0),.0002);
  EXPECT_EQ(raw.at("force1_world").at(0).at(2),-12.);
  EXPECT_EQ(ecm.Component<comp::ContactSensorData>(collisions[0])->Data().SerializeAsString(),
    native.SerializeAsString());
  EXPECT_THROW(nav::read_gazebo_contact_reference(robot,ecm,std::chrono::seconds(-1)),std::runtime_error);
  // Diagnostic details must not bloat every healthy 2ms gyro-reference packet.
  // Counts/loads remain present; <3 loaded feet retain the unmodified raw data.
  for (auto collision : collisions) {
    auto loaded_native=native;
    loaded_native.mutable_contact(0)->mutable_collision1()->set_id(collision);
    ecm.SetComponentData<comp::ContactSensorData>(collision,loaded_native);
  }
  const auto compact=nlohmann::json::parse(nav::read_gazebo_contact_reference(
    robot,ecm,std::chrono::seconds(5),true)->data());
  EXPECT_FALSE(compact.at("details_included").get<bool>());
  for (const auto & foot : compact.at("feet")) {
    EXPECT_EQ(foot.at("pair_count"),1);
    EXPECT_EQ(foot.at("sum_abs_force1_world_z_n"),12.);
    EXPECT_FALSE(foot.contains("pairs"));
  }
  ecm.SetComponentData<comp::ContactSensorData>(collisions[2],gz::msgs::Contacts());
  ecm.SetComponentData<comp::ContactSensorData>(collisions[3],gz::msgs::Contacts());
  const auto lost=nlohmann::json::parse(nav::read_gazebo_contact_reference(
    robot,ecm,std::chrono::seconds(6),true)->data());
  EXPECT_TRUE(lost.at("details_included").get<bool>());
  EXPECT_EQ(lost.at("feet").at(2).at("pairs").size(),0);
  EXPECT_EQ(lost.at("feet").at(2).at("sum_abs_force1_world_z_n"),0.);
  EXPECT_EQ(lost.at("feet").at(0).at("pairs").at(0).at("force1_world").at(0).at(2),-12.);
}
