// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <vector>
#include <gz/sim/components/Component.hh>
#include <gz/sim/components/Factory.hh>
#include <gz/sim/components/Serialization.hh>

namespace integrated_robot_navigation_sensors
{
// Diagnostic only: [input target, applied target, ramp seconds, write ROS ns].
// No Gazebo physics system consumes this Ch13-specific component as a command.
using PositionReference = gz::sim::components::Component<std::vector<double>,
  class PositionReferenceTag, gz::sim::serializers::VectorDoubleSerializer>;
GZ_SIM_REGISTER_COMPONENT("ch13_components.PositionReference", PositionReference)
}
