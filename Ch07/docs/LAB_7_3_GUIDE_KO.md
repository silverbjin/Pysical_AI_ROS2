# Ch07 §7.3 — 실제 ROS Image, cv_bridge 및 OpenCV Canny 실습

> ROS 2 Jazzy / Ubuntu 24.04. Ch07 §7.2 RGB-D 카메라는 OGRE2 SIGABRT 두 번으로 Issue #127 BLOCKED. 이번 절은 카메라 대신 **합성 ROS Image**를 사용하며, 카메라 기능 성공을 주장하지 않는다.

## 학습 목표

실제 ROS 2 Image 입력 → CvBridge의 BGR 변환 → OpenCV Grayscale/GaussianBlur/Canny → CvBridge mono8 출력 → 실제 ROS 2 Image 구독까지 검수한다. 토픽이 있다는 사실과 실제 픽셀/헤더까지 맞는지를 구별한다.

## 1. 환경과 빌드 — 터미널 A

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch07/ros2_ws
sudo apt-get install -y ros-jazzy-cv-bridge python3-opencv python3-numpy
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-select vision_basics
source install/setup.bash
ros2 pkg prefix vision_basics
ros2 pkg executables vision_basics | grep vision_processor
~~~

**예상:** Ch07 install 경로와 vision_basics vision_processor 실행 항목이 표시된다. setup.py 엔트리와 package.xml 직접 의존성을 보완했다.

## 2. 원본 이미지 처리 노드 — 터미널 A 유지

~~~bash
ros2 run vision_basics vision_processor --ros-args -p show_gui:=false
~~~

기본 show_gui:=true는 원본 강의 시연의 두 OpenCV 창을 유지한다. CI/GUI 없는 세션에서는 false로 ROS Image 처리만 검증한다. GUI가 보이는지 여부와 토픽 처리는 독립 상태이다.

## 3. 합성 이미지 발행과 실제 ROS 토픽 검수 — 새 터미널 B

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch07/ros2_ws
source install/setup.bash
ros2 topic info -v /camera/image_raw
ros2 topic info -v /camera/processed_image
~~~

기존 노드를 유지한 채, 저장소 루트에서 실제 독립 ROS Image 발행기 및 구독기를 실행한다.

~~~bash
cd ~/Pysical_AI_ROS2
CH07_73_RECEIPT="$PWD/ch07_73_receipt.json" \
python3 ci/ch07_73_image_roundtrip.py

echo "exit=$?"
python3 -m json.tool "$PWD/ch07_73_receipt.json"
~~~

**정상 로그 예상:**

~~~text
CH07_73_ACTUAL_ROS_IMAGE_CVBRIDGE_CANNY_MONO8_AND_STAMP_PASS processed_samples=3 edges=...
exit=0
~~~

검증기가 64×48 BGR 색상 사각형을 실제 DDS Publisher로 전송하고, 실제 vision_processor의 Image Subscriber→CvBridge→Canny→Publisher를 거친 3개 메시지를 구독한다. 출력 이미지 mono8 인코딩과 픽셀 크기, 입력과 정확히 일치하는 header.stamp와 camera_optical_frame, 독립 계산한 Canny 픽셀 배열 전체가 동일한지 검사한다. 로봇 카메라를 실행했다고 주장하지 않는다.

## 종료 및 범위

터미널 A Ctrl+C로 노드를 정리하고 터미널 B를 닫는다. 예상 로그만 있고 JSON/실제 메시지가 없으면 미완료다. GUI 창과 실제 Gazebo 렌더링은 검수하지 않는다.

공개 CI: .github/workflows/book-ch07-73-cvbridge.yml. 고정 Jazzy/Harmonic GHCR digest를 재사용하며 CvBridge/OpenCV만 임시 설치한다. 실제 CI 실행 후 SHA/원본 Artifact로 판정한다.

- Ch07 §7.3 synthetic ROS Image→cv_bridge→OpenCV→ROS Image: scoped PASS 또는 실제 결과에 따른 FAIL.
- Ch07 §7.2 Gazebo RGB-D Image 및 CameraInfo: BLOCKED (Issue #127), 이전 오류 재실행하지 않음.
- Depth 정렬, 실제 물체 인식, GUI, 실기: NOT_RUN. Ch10: HOLD.
