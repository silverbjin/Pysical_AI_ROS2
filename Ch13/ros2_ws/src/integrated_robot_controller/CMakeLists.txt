cmake_minimum_required(VERSION 3.16)
project(integrated_robot_controller)
find_package(ament_cmake REQUIRED)
# The derivative uses these exact installed public trajectory/parameter APIs.
# Do not silently build against an unreviewed upstream ABI/behavior change.
find_package(joint_trajectory_controller 4.42.1 EXACT REQUIRED)
find_package(realtime_tools 3.13.0 EXACT REQUIRED)
foreach(dependency controller_interface hardware_interface control_msgs control_toolbox
    trajectory_msgs lifecycle_msgs rclcpp rclcpp_action rclcpp_lifecycle pluginlib angles urdf)
  find_package(${dependency} REQUIRED)
endforeach()
add_library(ch13_joint_trajectory_controller SHARED src/joint_trajectory_controller.cpp)
target_compile_features(ch13_joint_trajectory_controller PUBLIC cxx_std_17)
target_include_directories(ch13_joint_trajectory_controller PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include> $<INSTALL_INTERFACE:include>)
target_link_libraries(ch13_joint_trajectory_controller
  joint_trajectory_controller::joint_trajectory_controller)
ament_target_dependencies(ch13_joint_trajectory_controller controller_interface hardware_interface
  control_msgs control_toolbox trajectory_msgs lifecycle_msgs rclcpp rclcpp_action
  rclcpp_lifecycle pluginlib angles urdf realtime_tools)
pluginlib_export_plugin_description_file(controller_interface controller_plugins.xml)
install(TARGETS ch13_joint_trajectory_controller LIBRARY DESTINATION lib)
install(DIRECTORY include/ DESTINATION include)
install(FILES LICENSE LICENSE.realtime_tools REUSE_MANIFEST.md UPSTREAM_SOURCES.json
  DESTINATION share/${PROJECT_NAME})

file(GLOB_RECURSE inputs CONFIGURE_DEPENDS RELATIVE ${CMAKE_CURRENT_SOURCE_DIR}
  include/*.hpp src/*.cpp test/*.cpp)
list(APPEND inputs CMakeLists.txt package.xml controller_plugins.xml LICENSE
  LICENSE.realtime_tools REUSE_MANIFEST.md UPSTREAM_SOURCES.json)
list(SORT inputs)
set(manifest "{\n")
foreach(input IN LISTS inputs)
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/${input}")
  file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/${input}" digest)
  string(APPEND manifest "  \"${input}\": \"${digest}\",\n")
endforeach()
string(REGEX REPLACE ",\n$" "\n" manifest "${manifest}")
string(APPEND manifest "}\n")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/source_manifest.json" "${manifest}")
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/source_manifest.json" DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_terminal_race test/test_terminal_race.cpp TIMEOUT 30)
  target_include_directories(test_terminal_race PRIVATE include)
  ament_target_dependencies(test_terminal_race rclcpp rclcpp_action control_msgs realtime_tools)
endif()
ament_package()
