# Ch07 §7.4 — ROS 2 HSV 빨강 물체 검출: 0/1/2개 테스트

> ROS 2 Jazzy / OpenCV, synthetic ROS Image 전용 실행 검수. Ch07 §7.2 실제 Gazebo RGB-D camera는 Issue #127 BLOCKED 상태를 유지한다.

## 목표

한 이미지에서 HSV 빨강 두 구간, Morphology opening/closing 및 최대 contour를 이용하여 물체의 중심 픽셀 (u,v)을 구하고 실제 ROS PointStamped로 발행한다. **PointStamped.point.z는 거리(m)가 아니라 검출된 contour 면적(px²)**이라는 기존 코드 계약을 이해한다.

미검출 시 기존 좌표가 이후 단계로 그대로 재사용되지 않도록 별도의 /camera/target_valid Bool이 매 이미지에 대해 true/false로 발행된다. 하위 단계에서는 이 값이 false이거나 오래되면 이전 좌표를 사용하지 않아야 한다. 실제 깊이와 물리 XYZ는 Ch07 §7.5의 별도 과제이다.

## 터미널 A — 패키지 준비 및 노드 실행

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch07/ros2_ws
sudo apt-get install -y ros-jazzy-cv-bridge python3-opencv python3-numpy
colcon build --symlink-install --packages-select vision_basics
source install/setup.bash
ros2 pkg executables vision_basics | grep object_detector
ros2 run vision_basics object_detector --ros-args -p min_area_px2:=500.0
~~~

**예상:** object_detector가 등록되어 실행되며, /camera/image_raw를 구독한다. 면적 임계값 500 px²는 교재 목표에 맞춘 기본값이다. 실제 Gazebo 카메라가 없더라도 노드는 ROS 입력을 기다린다.

## 터미널 B — 실제 토픽과 합성 영상 검증

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch07/ros2_ws
source install/setup.bash
ros2 topic info /camera/target_pixel -v
ros2 topic info /camera/target_valid -v
ros2 topic info /camera/detection_result -v

cd ~/Pysical_AI_ROS2
CH07_74_RECEIPT="$PWD/ch07_74_receipt.json" \
python3 ci/ch07_74_red_objects_probe.py

echo "exit=$?"
python3 -m json.tool "$PWD/ch07_74_receipt.json"
~~~

검증기에서 합성 bgr8 이미지 3종을 실제 ROS Publisher로 순서대로 전송한다.

- 빨강 1개: (u,v)=(140,110) 주변 최대 2픽셀 오차, 면적 500 px² 초과, 유효 true.
- 빨강 2개: 면적이 가장 큰 물체를 선택하여 (u,v)=(225,160) 주변 최대 2픽셀 오차 및 true.
- 빨강 0개: 현재 프레임의 /camera/target_valid false, 해당 타임스탬프의 새 좌표 메시지 없음.
- /camera/detection_result 토픽은 입력 header stamp·frame_id를 그대로 보존해야 한다.

**정상 로그 예상:**

~~~text
CH07_74_CASE_1_RED_VALID_PASS ...
CH07_74_CASE_2_MAX_CONTOUR_PASS ...
CH07_74_CASE_3_EMPTY_INVALIDATION_PASS
CH07_74_REAL_ROS_RED_TARGET_AND_INVALIDATION_SCOPED_PASS
exit=0
~~~

이 로그는 예상값이다. 실제 공개 CI에서 각 메시지, 결과 JSON 및 종료코드를 모두 검사한 후에만 PASS이다. 컨투어 소스만 존재하거나 ROS 토픽이 0건이면 NOT_RUN/FAIL 경계를 유지한다.

종료 시 터미널 A를 Ctrl+C로 닫고 B를 종료한다.

## CI 및 증거

공개 workflow: .github/workflows/book-ch07-74-detector.yml
단일 실행기: ci/ch07_74_once.sh
검증기: ci/ch07_74_red_objects_probe.py

같은 고정 GHCR digest와 CV Bridge/OpenCV 런타임만 사용한다. 실물·Gazebo 렌더러를 시작하지 않는다. 소스 SHA, 실제 ROS 토픽 발행·구독, 단일/복수/미검출 시나리오와 validity, 픽셀 좌표 및 면적, 원본 JSON/로그, 종료 상태를 보존한다.

- Ch07 §7.4 synthetic ROS Image 기반 빨강 HSV 검출: scoped PASS/FAIL(실측 기준).
- Ch07 §7.2 Gazebo RGB-D 렌더링: BLOCKED #127.
- Depth/3D XYZ, 실제 카메라 인식률, GUI, 물체 파지 및 실물 로봇: NOT_RUN.
- Ch10: HOLD.
