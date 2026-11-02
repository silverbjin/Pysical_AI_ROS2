// SPDX-License-Identifier: Apache-2.0
// Actual ros2_control plugin + actual ECM. Not native whole-robot acceptance.
#include <gtest/gtest.h>
#include <gz_ros2_control/gz_system_interface.hpp>
#include <pluginlib/class_loader.hpp>
#include <gz/sim/components/JointAxis.hh>
#include <gz/sim/components/JointType.hh>
#include <gz/sim/components/JointPosition.hh>
#include <gz/sim/components/JointVelocity.hh>
#include <gz/sim/components/JointPositionReset.hh>
#include <gz/sim/components/JointVelocityCmd.hh>
#include <gz/sim/components/JointForceCmd.hh>
#include <gz/sim/components/Pose.hh>
#include <limits>
#include "integrated_robot_navigation_sensors/position_reference.hpp"

namespace comp = gz::sim::components;
using Base = gz_ros2_control::GazeboSimSystemInterface;
using Return = hardware_interface::return_type;

struct PositionFixture
{
  gz::sim::EntityComponentManager ecm;
  hardware_interface::HardwareInfo info;
  std::map<std::string, gz::sim::Entity> joints;
  gz::sim::Entity root;
  rclcpp::Node::SharedPtr node;
  PositionFixture()
  {
    if (!rclcpp::ok()) {rclcpp::init(0, nullptr);}
    node = std::make_shared<rclcpp::Node>("navigation_position_system_test");
    root = ecm.CreateEntity();
    ecm.CreateComponent(root, comp::Pose(gz::math::Pose3d(1, 2, .45, 0, 0, 0)));
    info.name = "PositionFixture"; info.type = "system";
    for (const std::string name : {"hip", "finger"}) {
      const bool hinge = name == "hip";
      const auto entity = ecm.CreateEntity();
      joints[name] = entity;
      sdf::JointAxis axis;
      EXPECT_TRUE(axis.SetXyz(gz::math::Vector3d(0, 1, 0)).empty());
      axis.SetLower(hinge ? -1. : 0.); axis.SetUpper(hinge ? 1. : .03);
      axis.SetEffort(hinge ? 5. : 15.); axis.SetMaxVelocity(hinge ? 4. : .2);
      axis.SetDamping(hinge ? 2.02 : 15.02);
      ecm.CreateComponent(entity, comp::JointAxis(axis));
      ecm.CreateComponent(entity, comp::JointType(hinge ? sdf::JointType::REVOLUTE : sdf::JointType::PRISMATIC));
      hardware_interface::ComponentInfo joint;
      joint.name = name; joint.type = "joint";
      joint.parameters = {{"ch13_kp", "100"}, {"ch13_kd", hinge ? "2" : "15"}};
      joint.parameters["ch13_damping_mode"] = "native";
      joint.parameters["ch13_base_damping"] = "0.02";
      joint.parameters["ch13_native_damping"] = hinge ? "2.02" : "15.02";
      hardware_interface::InterfaceInfo command;
      command.name = "position"; command.min = hinge ? "-1" : "0";
      command.max = hinge ? "1" : "0.03";
      joint.command_interfaces.push_back(command);
      hardware_interface::InterfaceInfo q, qd;
      q.name = "position"; q.initial_value = hinge ? "0.1" : "0.015";
      qd.name = "velocity";
      joint.state_interfaces = {q, qd};
      info.joints.push_back(joint);
    }
  }
  void measurements()
  {
    ecm.SetComponentData<comp::JointPosition>(joints.at("hip"), {.2});
    ecm.SetComponentData<comp::JointVelocity>(joints.at("hip"), {.5});
    ecm.SetComponentData<comp::JointPosition>(joints.at("finger"), {.01});
    ecm.SetComponentData<comp::JointVelocity>(joints.at("finger"), {.002});
  }
};

TEST(NativePositionSystem, BoundedDampedEffortActualStatesAndNoRootOrVelocityWrites)
{
  pluginlib::ClassLoader<Base> loader("gz_ros2_control", "gz_ros2_control::GazeboSimSystemInterface");
  auto system = loader.createSharedInstance("integrated_robot_navigation_sensors/PositionPDSystem");
  PositionFixture f;
  ASSERT_TRUE(system->initSim(f.node, f.joints, f.info, f.ecm, 100));
  auto commands = system->export_command_interfaces();
  auto states = system->export_state_interfaces();
  ASSERT_EQ(commands.size(), 2u); ASSERT_EQ(states.size(), 4u);
  ASSERT_EQ(system->perform_command_mode_switch({"hip/position", "finger/position"}, {}), Return::OK);
  ASSERT_EQ(system->perform_command_mode_switch({"hip/position"}, {}), Return::ERROR);
  ASSERT_EQ(system->perform_command_mode_switch({"finger/velocity"}, {}), Return::ERROR);
  f.measurements();
  ASSERT_EQ(system->read(rclcpp::Time(1), rclcpp::Duration::from_seconds(.01)), Return::OK);
  EXPECT_DOUBLE_EQ(states[0].get_optional<double>().value(), .2);
  EXPECT_DOUBLE_EQ(states[1].get_optional<double>().value(), .5);
  ASSERT_TRUE(commands[0].set_value(.8)); ASSERT_TRUE(commands[1].set_value(.02));
  ASSERT_EQ(system->write(rclcpp::Time(1), rclcpp::Duration::from_seconds(.002)), Return::OK);
  EXPECT_DOUBLE_EQ(f.ecm.Component<comp::JointForceCmd>(f.joints.at("hip"))->Data().at(0), 5.);
  // Native DART integrates the declared viscous damper. External force is P
  // only; subtracting kd*qd here would double-count/reintroduce explicit D.
  EXPECT_NEAR(f.ecm.Component<comp::JointForceCmd>(f.joints.at("finger"))->Data().at(0), 1., 1e-12);
  EXPECT_FALSE(f.ecm.Component<comp::JointVelocityCmd>(f.joints.at("hip")));
  EXPECT_FALSE(f.ecm.Component<comp::JointVelocityCmd>(f.joints.at("finger")));
  EXPECT_EQ(f.ecm.Component<comp::Pose>(f.root)->Data(), gz::math::Pose3d(1, 2, .45, 0, 0, 0));
  ASSERT_TRUE(commands[0].set_value(std::numeric_limits<double>::quiet_NaN()));
  EXPECT_EQ(system->write(rclcpp::Time(2), rclcpp::Duration::from_seconds(.002)), Return::ERROR);
  EXPECT_DOUBLE_EQ(f.ecm.Component<comp::JointForceCmd>(f.joints.at("hip"))->Data().at(0), 0.);
  ASSERT_TRUE(commands[0].set_value(.3));
  EXPECT_EQ(system->write(rclcpp::Time(3), rclcpp::Duration::from_seconds(.002)), Return::ERROR);
}

TEST(NativePositionSystem, InvalidContractCannotPartiallyInitializeOrClaimNativeCommands)
{
  pluginlib::ClassLoader<Base> loader("gz_ros2_control", "gz_ros2_control::GazeboSimSystemInterface");
  auto system = loader.createSharedInstance("integrated_robot_navigation_sensors/PositionPDSystem");
  PositionFixture f;
  f.info.joints[1].parameters["ch13_kp"] = "nan";
  EXPECT_FALSE(system->initSim(f.node, f.joints, f.info, f.ecm, 100));
  for (auto [_, entity] : f.joints) {
    EXPECT_FALSE(f.ecm.Component<comp::JointForceCmd>(entity));
    EXPECT_FALSE(f.ecm.Component<comp::JointPositionReset>(entity));
  }
}

TEST(NativePositionSystem, CommandHandleExportCannotCreateASecondWriter)
{
  pluginlib::ClassLoader<Base> loader("gz_ros2_control", "gz_ros2_control::GazeboSimSystemInterface");
  auto system = loader.createSharedInstance("integrated_robot_navigation_sensors/PositionPDSystem");
  PositionFixture f;
  ASSERT_TRUE(system->initSim(f.node, f.joints, f.info, f.ecm, 100));
  auto owned = system->export_command_interfaces();
  ASSERT_EQ(owned.size(), 2u);
  EXPECT_TRUE(system->export_command_interfaces().empty());
}

TEST(NativePositionSystem, MissingNativeDampingCannotActivateAnExplicitDerivativeFallback)
{
  pluginlib::ClassLoader<Base> loader("gz_ros2_control", "gz_ros2_control::GazeboSimSystemInterface");
  auto system = loader.createSharedInstance("integrated_robot_navigation_sensors/PositionPDSystem");
  PositionFixture f;
  auto axis = f.ecm.Component<comp::JointAxis>(f.joints.at("hip"))->Data();
  axis.SetDamping(.02);
  f.ecm.SetComponentData<comp::JointAxis>(f.joints.at("hip"), axis);
  EXPECT_FALSE(system->initSim(f.node, f.joints, f.info, f.ecm, 100));
  EXPECT_FALSE(f.ecm.Component<comp::JointForceCmd>(f.joints.at("hip")));
}

static void g1_reference(PositionFixture & f)
{
  f.info.hardware_parameters["ch13_g1_reference_experiment"] = "true";
  f.info.joints[0].name = "fr_hip_joint";
  f.joints["fr_hip_joint"] = f.joints.at("hip");
  f.info.joints[0].parameters["ch13_reference_ramp_s"] = "0.02";
}

TEST(NativePositionSystem, OptInG1LegReferenceIsContinuousWithoutChangingNativeGainsOrForceCap)
{
  pluginlib::ClassLoader<Base> loader("gz_ros2_control", "gz_ros2_control::GazeboSimSystemInterface");
  auto system = loader.createSharedInstance("integrated_robot_navigation_sensors/PositionPDSystem");
  PositionFixture f; g1_reference(f);
  ASSERT_TRUE(system->initSim(f.node, f.joints, f.info, f.ecm, 100));
  auto commands = system->export_command_interfaces();
  ASSERT_EQ(system->perform_command_mode_switch({"fr_hip_joint/position"}, {}), Return::OK);
  f.measurements();
  f.ecm.SetComponentData<comp::JointPosition>(f.joints.at("hip"), {.1});
  ASSERT_TRUE(commands[0].set_value(.12));
  for (const auto [ns, force] : std::vector<std::pair<int64_t,double>>{
      {1000000000,0.}, {1002000000,.2}, {1010000000,1.}, {1020000000,2.}}) {
    ASSERT_EQ(system->write(rclcpp::Time(ns), rclcpp::Duration::from_seconds(.002)), Return::OK);
    EXPECT_NEAR(f.ecm.Component<comp::JointForceCmd>(f.joints.at("hip"))->Data().at(0), force, 1e-12);
    const auto * trace=f.ecm.Component<integrated_robot_navigation_sensors::PositionReference>(f.joints.at("hip"));
    ASSERT_NE(trace,nullptr);
    ASSERT_EQ(trace->Data().size(),4u);
    EXPECT_DOUBLE_EQ(trace->Data()[0],.12);
    EXPECT_NEAR(trace->Data()[1],.1+force/100.,1e-12);
    EXPECT_DOUBLE_EQ(trace->Data()[2],.02);
    EXPECT_DOUBLE_EQ(trace->Data()[3],static_cast<double>(ns));
  }
  ASSERT_TRUE(commands[0].set_value(.8));
  ASSERT_EQ(system->write(rclcpp::Time(1040000000), rclcpp::Duration::from_seconds(.002)), Return::OK);
  ASSERT_EQ(system->write(rclcpp::Time(1060000000), rclcpp::Duration::from_seconds(.002)), Return::OK);
  EXPECT_DOUBLE_EQ(f.ecm.Component<comp::JointForceCmd>(f.joints.at("hip"))->Data().at(0), 5.);
  EXPECT_FALSE(f.ecm.Component<comp::JointVelocityCmd>(f.joints.at("hip")));
  EXPECT_EQ(f.ecm.Component<comp::Pose>(f.root)->Data(), gz::math::Pose3d(1,2,.45,0,0,0));
}

TEST(NativePositionSystem, NewTargetAndDeactivateHoldTheAppliedReferenceRatherThanJumpingToPendingEndpoint)
{
  pluginlib::ClassLoader<Base> loader("gz_ros2_control", "gz_ros2_control::GazeboSimSystemInterface");
  auto system = loader.createSharedInstance("integrated_robot_navigation_sensors/PositionPDSystem");
  PositionFixture f; g1_reference(f);
  ASSERT_TRUE(system->initSim(f.node, f.joints, f.info, f.ecm, 100));
  auto commands = system->export_command_interfaces();
  ASSERT_EQ(system->perform_command_mode_switch({"fr_hip_joint/position"}, {}), Return::OK);
  f.measurements(); f.ecm.SetComponentData<comp::JointPosition>(f.joints.at("hip"), {.1});
  commands[0].set_value(.12);
  ASSERT_EQ(system->write(rclcpp::Time(1000000000), rclcpp::Duration::from_seconds(.002)), Return::OK);
  commands[0].set_value(.13);
  ASSERT_EQ(system->write(rclcpp::Time(1010000000), rclcpp::Duration::from_seconds(.002)), Return::OK);
  EXPECT_NEAR(f.ecm.Component<comp::JointForceCmd>(f.joints.at("hip"))->Data().at(0),1.,1e-12);
  ASSERT_EQ(system->perform_command_mode_switch({}, {"fr_hip_joint/position"}), Return::OK);
  ASSERT_EQ(system->write(rclcpp::Time(1020000000), rclcpp::Duration::from_seconds(.002)), Return::OK);
  EXPECT_NEAR(f.ecm.Component<comp::JointForceCmd>(f.joints.at("hip"))->Data().at(0),1.,1e-12);
  ASSERT_EQ(system->perform_command_mode_switch({"fr_hip_joint/position"}, {}), Return::OK);
  EXPECT_NEAR(commands[0].get_optional<double>().value(),.11,1e-12);
  ASSERT_EQ(system->write(rclcpp::Time(1030000000), rclcpp::Duration::from_seconds(.002)), Return::OK);
  EXPECT_NEAR(f.ecm.Component<comp::JointForceCmd>(f.joints.at("hip"))->Data().at(0),1.,1e-12);
  EXPECT_EQ(system->write(rclcpp::Time(1020000000), rclcpp::Duration::from_seconds(.002)), Return::ERROR);
  EXPECT_DOUBLE_EQ(f.ecm.Component<comp::JointForceCmd>(f.joints.at("hip"))->Data().at(0),0.);
}

TEST(NativePositionSystem, ReferenceExperimentCannotEnableSilentlyOrAffectArmAndFingerCommands)
{
  pluginlib::ClassLoader<Base> loader("gz_ros2_control", "gz_ros2_control::GazeboSimSystemInterface");
  for (int invalid : {0,1,2}) {
    auto system = loader.createSharedInstance("integrated_robot_navigation_sensors/PositionPDSystem");
    PositionFixture f; g1_reference(f);
    if (invalid==0) {f.info.hardware_parameters.clear();}
    if (invalid==1) {f.info.joints[0].parameters["ch13_reference_ramp_s"]="0.01";}
    if (invalid==2) {f.info.joints[1].parameters["ch13_reference_ramp_s"]="0.02";}
    EXPECT_FALSE(system->initSim(f.node, f.joints, f.info, f.ecm, 100));
    EXPECT_FALSE(f.ecm.Component<comp::JointForceCmd>(f.joints.at("hip")));
  }
}
