// SPDX-License-Identifier: Apache-2.0
#include "integrated_robot_navigation_sensors/tf_provenance.hpp"
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
    if (arguments.size() != 2) {throw std::invalid_argument("usage: tf_provenance NEW_OUTPUT.jsonl");}
    descriptor = ::open(arguments[1].c_str(), O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC, 0600);
    if (descriptor < 0) {throw std::runtime_error(std::strerror(errno));}
    {
      auto observer = std::make_shared<integrated_robot_navigation_sensors::TfProvenanceObserver>(
        [descriptor](const nlohmann::json & row) {
          const auto line = row.dump()+"\n";
          size_t offset = 0;
          while (offset < line.size()) {
            const auto count = ::write(descriptor, line.data()+offset, line.size()-offset);
            if (count < 0 && errno == EINTR) {continue;}
            if (count <= 0) {throw std::runtime_error("TF provenance write failed");}
            offset += static_cast<size_t>(count);
          }
        });
      rclcpp::spin(observer);
    }  // subscribers are destroyed before the output descriptor
    if (::close(descriptor) != 0) {throw std::runtime_error("TF provenance close failed");}
    descriptor = -1;
    rclcpp::shutdown();
    return 0;
  } catch (const std::exception & error) {
    std::cerr << "TF provenance failure: " << error.what() << std::endl;
    if (descriptor >= 0) {::close(descriptor);}
    rclcpp::shutdown();
    return 1;
  }
}
