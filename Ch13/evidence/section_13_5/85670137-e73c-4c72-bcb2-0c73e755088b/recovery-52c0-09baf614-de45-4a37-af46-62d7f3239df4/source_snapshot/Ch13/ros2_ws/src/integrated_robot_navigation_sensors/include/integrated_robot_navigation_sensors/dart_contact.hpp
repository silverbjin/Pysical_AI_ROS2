// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <cstddef>
#include <string>

namespace integrated_robot_navigation_sensors
{
struct DartContactState
{
  double before_m, effective_m;
  std::string header_version, library_path;
};
DartContactState inspect_dart_contact();  // read-only public native getter
DartContactState configure_g1_dart_contact(double requested_m, size_t worlds, bool explicit_g1);
}
