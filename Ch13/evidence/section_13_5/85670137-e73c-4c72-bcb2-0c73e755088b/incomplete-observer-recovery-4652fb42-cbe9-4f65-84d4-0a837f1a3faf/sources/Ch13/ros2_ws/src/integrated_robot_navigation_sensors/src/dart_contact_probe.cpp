// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/dart_contact.hpp"
#include <iostream>
#include <nlohmann/json.hpp>
int main()
{
  const auto state=integrated_robot_navigation_sensors::inspect_dart_contact();
  std::cout<<nlohmann::json{{"current_m",state.effective_m},
    {"header_version",state.header_version},{"library_path",state.library_path}}.dump()<<'\n';
}
