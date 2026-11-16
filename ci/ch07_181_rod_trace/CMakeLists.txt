cmake_minimum_required(VERSION 3.16)
project(ch07_181_rod_trace LANGUAGES CXX)
find_package(gz-sim8 REQUIRED)
find_package(gz-plugin2 REQUIRED COMPONENTS register)
add_library(ch07_181_rod_trace SHARED rod_trace.cc)
target_compile_features(ch07_181_rod_trace PRIVATE cxx_std_17)
target_link_libraries(ch07_181_rod_trace gz-sim8::gz-sim8 gz-plugin2::gz-plugin2)

# Reuse proven #187 ECS observer API in the same one-time CMake configure.
add_library(ch07_181_finger_ecs_trace SHARED finger_ecs_trace.cc)
target_compile_features(ch07_181_finger_ecs_trace PRIVATE cxx_std_17)
target_link_libraries(ch07_181_finger_ecs_trace gz-sim8::gz-sim8 gz-plugin2::gz-plugin2)
