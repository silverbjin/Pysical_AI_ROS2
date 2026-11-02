// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <optional>
#include <stdexcept>

namespace integrated_robot_navigation_sensors
{
// Bounded diagnostic burst at a raw loaded-to-unloaded edge. Never a contact
// acceptance rule, sensor filter, force substitute or controller state machine.
class ContactDetailWindow
{
  std::optional<unsigned> previous_;
  unsigned remaining_{0};
public:
  bool observe(unsigned loaded_mask)
  {
    if (loaded_mask>15) {throw std::runtime_error("invalid four-foot diagnostic mask");}
    if (previous_ && ((*previous_ & ~loaded_mask)!=0)) {remaining_=10;}
    previous_=loaded_mask;
    if (!remaining_) {return false;}
    --remaining_;
    return true;
  }
};
}
