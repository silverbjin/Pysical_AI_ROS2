// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/control_clock_relay.hpp"
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>
#include <iostream>
#include <stdexcept>

int main(int argc, char ** argv)
{
  int descriptor = -1;
  try {
    rclcpp::init(argc, argv);
    const auto arguments = rclcpp::remove_ros_arguments(argc, argv);
    if (arguments.size() > 2) {throw std::invalid_argument("usage: control_clock_relay [NEW_TRACE.jsonl]");}
    if (arguments.size() == 2) {
      descriptor = ::open(arguments[1].c_str(), O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC, 0600);
      if (descriptor < 0) {throw std::runtime_error(std::strerror(errno));}
    }
    int result;
    {
      auto relay = std::make_shared<integrated_robot_navigation_sensors::ControlClockRelay>(
        [descriptor](const nlohmann::json & row) {
          if (descriptor < 0) {return;}
          const auto line = row.dump()+"\n";
          size_t offset = 0;
          while (offset < line.size()) {
            const auto count = ::write(descriptor, line.data()+offset, line.size()-offset);
            if (count < 0 && errno == EINTR) {continue;}
            if (count <= 0) {throw std::runtime_error("control clock trace write failed");}
            offset += static_cast<size_t>(count);
          }
        });
      rclcpp::spin(relay);
      relay->finish();
      result = relay->report().at("fault").get<std::string>().empty() ? 0 : 1;
    }  // callbacks/subscriptions/timer destroyed before file descriptor
    if (descriptor >= 0 && ::close(descriptor) != 0) {throw std::runtime_error("control clock close failed");}
    descriptor = -1;
    rclcpp::shutdown();
    return result;
  } catch (const std::exception & error) {
    std::cerr << "control clock failure: " << error.what() << std::endl;
    if (descriptor >= 0) {::close(descriptor);}
    rclcpp::shutdown();
    return 1;
  }
}
