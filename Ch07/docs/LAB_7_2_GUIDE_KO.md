# LAB_7_2_GUIDE_KO — 7.2절 Gazebo Harmonic 카메라 센서 설정 및 데이터 수신

> 대상: Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic, Ch07 단독 실습
> 기준 commit: a318c04a69a003e5c5d5998f077f2b8a8f36a1a5 (2026-10-20) · 상태: **BLOCKED — 센서 구성과 실행 경로 불충분**
> 실제 실행 검증: **미수행**. 아래 코드는 교재 실습 절차 및 실행 후 검증 기준이며, 출력 사례를 실측 결과로 제시하지 않는다.

## 실습 전 원칙
- 리포지토리 루트의 **Ch07/ros2_ws**를 작업 공간으로 사용한다. 설치된 패키지명은 **vision_basics**이다(원고의 my_robot_vision과 다름).
- 터미널마다 /opt/ros/jazzy/setup.bash → Ch07/ros2_ws/install/setup.bash 순서로 source한다. Ch08~Ch13 overlay가 AMENT_PREFIX_PATH에 섞이면 검증 결과가 바뀔 수 있다.
- 실제 카메라, 액션 서버, Gazebo controller, MoveIt 2 설정은 **존재 확인이 완료된 후** 해당 노드나 미션을 실행한다.
- ROS 관련 Python 바인딩은 Ubuntu/ROS apt 패키지를 우선한다. 글로벌 pip 설치가 ROS의 NumPy/Qt ABI와 충돌하지 않도록 주의한다.
- Gazebo에서의 노드 실행, 실제 팔/그리퍼 명령은 사람이나 실물 하드웨어가 없는 독립 시뮬레이션에서만 검증한다.

## 사전 점검
~~~bash
# Ubuntu 24.04 / ROS 2 Jazzy 전제. Ch07 단독 overlay에서 실행
source /opt/ros/jazzy/setup.bash
cd Pysical_AI_ROS2/Ch07/ros2_ws
echo "$ROS_DISTRO"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | head -20
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --event-handlers console_direct+
source install/setup.bash
ros2 pkg prefix vision_basics
~~~
~~~bash
# 실제 모델에 카메라와 optical frame이 있는지 소스 확인
grep -n 'camera_link\|camera_optical_frame\|<sensor' src/vision_basics/urdf/my_robot.urdf.xacro || true
# 원고에 적힌 경로가 있는지 확인 (없는 경로를 만들어졌다고 가정하지 않는다)
find src -type f \( -name '*camera*.xacro' -o -name '*simulation*.launch.py' -o -name '*.sdf' \) | sort
ros2 pkg executables vision_basics
ros2 pkg prefix my_robot_description || true
~~~

**예상 상태(원본):** 위 URDF에 카메라 정의가 없고, simple_image_subscriber는 ros2 pkg executables에서 발견되지 않을 수 있다. 이때 이미지를 받으려고 다음 단계로 넘어가지 말고 구성 결함을 먼저 해결한다.

## 센서/브리지 통합 후 검증
실제 camera가 포함된 Gazebo launch 또는 world를 먼저 실행한다. 어떤 launch 파일이 존재하는지 find로 확인한 뒤 그 **실제 파일명**을 사용한다. 확인하지 않은 simulation.launch.py 명령은 사용하지 않는다.

~~~bash
gz topic -l | grep -E 'camera|image|depth'
ros2 topic list -t | grep -E 'camera|image|depth'
ros2 topic info -v /camera/image_raw
ros2 topic hz /camera/image_raw
ros2 topic echo --once /camera/camera_info
ros2 run rqt_image_view rqt_image_view
~~~

RGB-D 구현을 택했다면 /camera/depth/image_raw의 encoding(32FC1/16UC1), 단위(m/mm), 유효 픽셀 비율과 Color/Depth의 정렬 여부도 확인한다.

## 증거·오류 구분
- gz 토픽 없음: 센서 생성/렌더러/시뮬레이션 일시정지/월드 plugin 문제.
- gz는 있음, ros2는 없음: ros_gz_bridge 토픽명·타입·방향 확인.
- 토픽은 있으나 구독 0: QoS 정책과 frame_id 확인.
- RViz 실행 오류: my_robot_description 및 파일 경로 문제를 카메라 실패와 구분.

**완료 기준:** 화면 1장, hz 측정값, CameraInfo K, image frame_id와 optical TF, depth 계약을 기록한다. 이번 검토에서는 해당 실행 검증을 수행하지 못했다.

## 기록·제출물
실습자는 git rev-parse HEAD, ros2 doctor --report, colcon build 종료 코드, 실행한 명령, topic/TF/action 확인 결과, 정상 및 실패 사례(스크린샷·로그)를 함께 남긴다. **정적 점검 결과와 실측 결과를 혼동하지 않는다.**

관련 리뷰: [SECTION_7_2_REPORT_KO.md](SECTION_7_2_REPORT_KO.md).
