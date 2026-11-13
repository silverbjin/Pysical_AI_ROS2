# Ch07 §7.5 — 픽셀·Depth·CameraInfo·TF를 이용한 3D 좌표 변환

> ROS 2 Jazzy / Ubuntu 24.04. 시뮬레이션 전용 MVP. Ch07 §7.2 실제 Gazebo RGB-D 센서는 OGRE2 SIGABRT로 Issue #127 **BLOCKED** 상태이며, 이번 절은 **합성 depth 및 CameraInfo** 입력만 시험한다.

## 배울 것

2D 검출 좌표 (u,v), 실제 깊이 Z(m), 카메라 내부 파라미터 fx,fy,cx,cy를 이용하여 광학 좌표계의 3D 점을 계산한다.

- X=(u-cx)*Z/fx, Y=(v-cy)*Z/fy, Z=측정 깊이.
- 입력: /camera/target_pixel geometry_msgs/PointStamped, /camera/target_valid std_msgs/Bool, /camera/depth/image_raw sensor_msgs/Image, /camera/camera_info sensor_msgs/CameraInfo, /tf_static.
- 출력: /camera/target_3d_base geometry_msgs/PointStamped, frame_id=base_link, 원본 이미지 stamp 유지.
- §7.4 detector의 PointStamped.point.z는 픽셀 면적(px²)이며, 깊이(m)로 절대 사용하지 않는다.
- depth encoding 32FC1일 때 단위 m, 16UC1일 때 **교육용 일반적인 mm 가정**으로 m 변환한다. 다른 센서의 실제 단위는 별도 확인한다.

## 전제와 안전 경계

실측 RGB-D color/depth 정렬, 물체의 실제 표면 깊이, 손목 이동 중 TF, grasp 자세/TCP offset, 카메라 보정 오차는 **이번 합성 테스트로 검증하지 않는다**. Depth 입력이 없거나 NaN/0/과거 시각/내부 파라미터 오류/프레임 불일치/target_valid=false라면 3D 좌표를 게시하지 않아야 한다.

이 코드는 3D **표면점 후보**만 출력한다. §7.6~§7.7에서 실제 로봇 팔/그리퍼 목표로 연결하지 않는다.

## 준비 — 터미널 A

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch07/ros2_ws
sudo apt-get install -y ros-jazzy-tf2-ros
colcon build --symlink-install --packages-select vision_basics
source install/setup.bash
ros2 pkg executables vision_basics | grep coord_transformer
~~~

다음은 **합성 시험용 정적 TF**이며 실제 로봇 설치 오프셋이 아니다.

~~~bash
ros2 run tf2_ros static_transform_publisher \
  --x 0.2 --y 0.1 --z 0.4 \
  --roll 0 --pitch 0 --yaw 0 \
  --frame-id base_link --child-frame-id camera_optical_frame
~~~

터미널 A는 종료하지 않는다.

## 변환 노드 — 새 터미널 B

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch07/ros2_ws
source install/setup.bash
ros2 run vision_basics coord_transformer
~~~

노드는 실제 ROS 입력을 기다린다. /camera/target_valid=false 상태에서는 아무 3D 목표도 출력하지 않는다.

## 실제 ROS 통신 검수 — 새 터미널 C

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch07/ros2_ws && source install/setup.bash
cd ~/Pysical_AI_ROS2
CH07_75_RECEIPT="$PWD/ch07_75_receipt.json" \
python3 ci/ch07_75_depth_projection_probe.py
echo "exit=$?"
python3 -m json.tool "$PWD/ch07_75_receipt.json"
~~~

검수기는 합성 80×60 Image, K=[fx=60,fy=60,cx=40,cy=30], pixel=(48,34), 표면깊이=0.5m 또는 0.75m, translation=(0.2,0.1,0.4)m의 항등 회전을 사용한다. 32FC1과 16UC1 두 가지 유효 케이스에서 기대한 base_link 위치와 최대 0.002m 오차 이내인지 검증한다.

이어 **NaN depth, zero depth, fx=0, 오래된 stamp, depth/픽셀 stamp 불일치, optical frame 불일치, target_valid=false** 등 7가지에 대해서 해당 stamp의 3D 점이 발행되지 않아야 한다.

**기대 로그 패턴(실제 실행 결과가 아님):**

~~~text
CH07_75_VALID_32FC1_PASS ...
CH07_75_VALID_16UC1_PASS ...
CH07_75_INVALID_DEPTH_NAN_FAIL_CLOSED_PASS
CH07_75_INVALID_DEPTH_ZERO_FAIL_CLOSED_PASS
CH07_75_INVALID_CAMERA_K_FAIL_CLOSED_PASS
CH07_75_INVALID_STALE_STAMP_FAIL_CLOSED_PASS
CH07_75_INVALID_MISALIGNED_STAMP_FAIL_CLOSED_PASS
CH07_75_INVALID_OPTICAL_FRAME_FAIL_CLOSED_PASS
CH07_75_invalid_validity_FAIL_CLOSED_PASS
CH07_75_ACTUAL_ROS_SYNTHETIC_DEPTH_CAMERAINFO_TF_SCOPED_PASS
~~~

다음과 같은 경우에는 PASS를 선언하지 않는다. 결과 토픽 발행 없이 수학 함수만 통과한 경우, 불량 입력에서 잘못된 3D 점이 나간 경우, TF를 확인하지 못한 경우, 동작 후 종료가 SIGKILL까지 확대된 경우 등이다.

종료: 터미널 B에서 Ctrl+C, 터미널 A에서 Ctrl+C, 그다음 터미널 C를 종료한다.

## CI·증거·판정

공개 workflow: .github/workflows/book-ch07-75-depth-tf.yml
검수기: ci/ch07_75_once.sh, ci/ch07_75_depth_projection_probe.py

기존 GHCR digest sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f를 그대로 사용하고 tf2_ros만 필요시 임시 설치한다. 실제 공개 Actions 원본 로그와 JSON 영수증, 소스 SHA, Artifact가 있어야 **Ch07 §7.5 synthetic ROS backprojection scoped PASS**를 선언할 수 있다.

Ch07 §7.2 RGB-D 렌더링 BLOCKED #127, Ch11 SaveMap Service FAIL #130, Ch10 HOLD는 별도로 유지한다. 정확한 grasp pose/장애물/실물 구동, depth 정렬 성능은 NOT_RUN.
