cmake_minimum_required(VERSION 3.16)
project(integrated_robot_interfaces)
find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "action/PickObject.action"
  "srv/SetMode.srv"
  DEPENDENCIES geometry_msgs
)
ament_export_dependencies(rosidl_default_runtime)
ament_package()
