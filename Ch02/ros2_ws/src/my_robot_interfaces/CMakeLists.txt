cmake_minimum_required(VERSION 3.8)
project(my_robot_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# 1. 필수 패키지 찾기
find_package(ament_cmake REQUIRED)
# rosidl_default_generators: 인터페이스 코드를 생성해주는 핵심 도구
find_package(rosidl_default_generators REQUIRED) 

# 2. 인터페이스 파일 등록: 우리가 만든 파일들을 리스트에 추가한다.
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/HardwareStatus.msg"
  "srv/ComputeRectangleArea.srv"
  "action/CountUntil.action"  # <-- 이 줄 추가
)

# 3. 의존성 내보내기
ament_export_dependencies(rosidl_default_runtime)

ament_package()
