# Ch07 §7.2 — 실제 Depth / PointCloud2 프레임 계약 보완 (#163)

> 2026-11-14 KST · ROS 2 Jazzy + Gazebo Harmonic OGRE2 · 기존 원본 RGB-D 모델과 원본 SDF 파일 불변 · **Headless 시뮬레이션 좁은 범위 PASS**, GUI·§7.7 파지·물리 로봇 미검증. Ch10 #123 HOLD.

## 1. 발견된 실제 문제

기존 [#127 RGB](https://github.com/silverbjin/Pysical_AI_ROS2/issues/127)와 [#161 Depth/PointCloud 데이터](https://github.com/silverbjin/Pysical_AI_ROS2/issues/161)는 각각 통과했지만, 실제 3D 좌표의 광학 프레임 적합성은 검증하지 않았다.

새 전용 공개 CI [#43473118466](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43473118466) / [원본 Artifact #14061678671](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43473118466/artifacts/14061678671)의 동일 타임스탬프·동일 픽셀 70쌍 검사:

- `/camera/depth_image` + `/camera/camera_info`: 실제 `camera_optical_frame` + K를 사용해 픽셀 (u,v)에서 광학 좌표를 계산했다.
- 기존 `/camera/points` PointCloud2: 헤더는 `camera_optical_frame`이나 XYZ 값은 **Gazebo +X 전방 좌표**였다.
- XYZ를 그대로 광학 좌표라고 오해하면 중앙값 **1.181340m 오차**. +X 전방 값을 optical로 회전 `(-Y, -Z, X)` 하면 **0.001065m**. 이 최초 진단 CI는 **실패(rc42)**가 맞다. 오류와 정상 종료를 혼동하지 않는다.
- Gazebo Sensors의 +X-forward와 ROS optical +Z-forward 관례 차이는 [gz-sensors #488](https://github.com/gazebosim/gz-sensors/issues/488)에서도 설명한다. **프레임 헤더 문자열을 맞춘 것만으로 값이 자동 회전하지 않는다.**

## 2. 최소 해결책 — PointCloud2 전용 브리지만 프레임 재지정

**센서 모델, 원본 Gazebo 포인트 좌표값, RGB/Depth 발행 코드 변경 없이** ROS-GZ 브리지를 두 프로세스로 분리한다.

기존 실제 Gazebo 카메라가 실행되는 동안, **터미널 A**:

~~~bash
source /opt/ros/jazzy/setup.bash
# Ch07 overlay도 필요한 경우: source <Ch07>/ros2_ws/install/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
  '/camera/image@sensor_msgs/msg/Image[gz.msgs.Image' \
  '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo' \
  '/camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image' \
  --ros-args -r /camera/image:=/camera/image_raw
~~~

**터미널 B** — 실제 XYZ가 +X 전방인 PointCloud2에만 올바른 물리 프레임 선언:

~~~bash
source /opt/ros/jazzy/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
  '/camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked' \
  --ros-args -p override_frame_id:=camera_link
~~~

이 설정을 사용하면 PointCloud2는 `frame_id=camera_link`이고, Depth/CameraInfo는 `camera_optical_frame`을 유지한다. **원본 Xacro의 정적 TF `camera_link → camera_optical_frame`**를 사용하면 PointCloud2를 ROS optical(+Z 전방)으로 올바르게 변환할 수 있다. 포인트클라우드의 실제 XYZ 바이트를 회전 없이 유지하기 때문에 헤더와 데이터의 물리 좌표축이 일치한다.

종료 시 각 브리지 터미널에서 Ctrl+C를 눌러 종료하고, Gazebo 세션은 별도 종료한다. 원샷 시뮬레이터는 종료 후 토픽이 사라지는 것이 정상이다.

## 3. 검증한 실제 범위

- [수정 공개 CI #43473755483](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43473755483) **SUCCESS**.
- [원본 Artifact #14062231150](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43473755483/artifacts/14062231150) ZIP SHA256 `6705ccb4b102ceb210555edd99b54ab192a33ff364246857f34dd8fe7ca5b439`, 원본 업로드 로그와 일치. 총 29개 파일, `optical_pixel_receipt.json`과 `result.json` 직접 검사.
- 검증된 브랜치 소스 HEAD `1a25fcfe25930ad935fc212d36938722f018e873`, CI synthetic merge checkout `bf0ea12...`. 기존 Xacro blob `629177034e12c38ffe46f635c7e38112e7cc6c2d`, 월드 blob `54478268aabc5a75a48a0283e1deb7917ce74ddd` 보존. 공통 GHCR digest `sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f` 재사용.
- 실제 매칭된 스탬프 2개, **동일 픽셀/시각 표본 70개**, RGB-Depth 공통 스탬프 2개. **카메라 좌표→광학 좌표의 수치 오차 중앙값 0.001064882m**, 보정 전 광학으로 잘못 해석한 오차 중앙값 1.181222781m.
- 최종 로그 `CH07_163_MATCHED_PIXEL_CAMERA_LINK_NATIVE_X_FORWARD_CONFIRMED`, `CH07_163_FINAL stage=CH07_163_POINTCLOUD_FRAME_CONTRACT_SCOPED_PASS rc=0 shutdown=OWNED_GROUPS_EXITED_NO_SIGKILL`. 시뮬레이터 자연 종료 0, SIGKILL 없음.
- 원본 세계의 z=1m 표적은 애초 시야 밖이라 새로운 **테스트 임시 세계 사본에서만** 기존 visual_target을 z=2.29m로 옮겼다. 원본 파일은 변조하지 않았다.

**SCOPED PASS:** 동일 시각/동일 픽셀 Depth·PointCloud2 수치 대응 및 올바른 cloud/native-frame 선언을 거친 ROS optical 투영(테스트 표적 조건), 정상 종료.

**NOT_RUN:** RGB 영상의 색상-Depth 실제 픽셀 정렬/색상 매칭, 카메라 외부·내부 파라미터의 물리 정확도, RViz GUI, WSLg/하드웨어, Ch07 §7.7 물리 파지, 전체 101 LAB. PointCloud2 데이터를 optical XYZ로 **변환해 새 토픽으로 발행한 것**도 아니므로, 광학 좌표를 필요로 하는 노드는 반드시 TF 변환해서 사용해야 한다. 코드 원본/오래된 RGB 전용 CI는 반복하지 않았다.

## 4. 실습 시 확인

시뮬레이터가 살아 있는 별도 터미널에서:

~~~bash
ros2 topic info -v /camera/points
ros2 topic echo /camera/points --once --field header
ros2 topic echo /camera/depth_image --once --field header
ros2 topic echo /camera/camera_info --once --field header
ros2 run tf2_ros tf2_echo camera_link camera_optical_frame
~~~

기대 헤더는 **PointCloud2 = `camera_link`**, **Depth/Info = `camera_optical_frame`**이다. 이 CLI 문자열 자체는 수치 정합 증거가 아니며, 실제 정합 증거는 전용 CI의 `optical_pixel_receipt.json`에서 확인한다. TF와 데이터 변환을 수행하는 소비자 코드는 각자 별도로 테스트해야 한다.
