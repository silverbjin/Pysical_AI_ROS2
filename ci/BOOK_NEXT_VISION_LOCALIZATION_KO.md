# 후속 실습 검수 — Ch10 HOLD 유지 / Ch07 카메라 / Ch11 EKF·SLAM

실행: GitHub Actions **Book next camera and localization verification (Ch10 HOLD)**

## 소스·런타임 경계

- 고정 베이스 이미지는 검증된 GHCR digest `sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f`이다. Dockerfile을 재빌드하지 않는다.
- Ch07은 `my_robot.ros2_camera_gazebo.urdf.xacro` 원본을 사용하되, CI 전용 world fixture로 Gazebo Sensors 플러그인을 실행한다. GUI 포함 원본 Launch 자체를 실행한 결과로 승격하지 않는다.
- Ch11은 기존 `ci/docker/next_scope.sh`와 원본 sensor_figure_world.sdf, ros_gz_bridge.yaml, sim_odometry, ekf.yaml, slam.launch.py를 사용한다. 베이스 이미지에 없던 `robot_localization` / `slam_toolbox` 두 apt 패키지만 컨테이너 실행 중 추가하고 실제 설치 버전을 Evidence에 기록한다. 따라서 최종 실행 환경 전체가 기존 이미지 digest와 동일하다고 주장하지 않는다.
- 각 Job은 독립 ROS_DOMAIN_ID / GZ_PARTITION, 시간 제한과 종료 회수 로그, 소스 SHA 및 원본 Artifact를 보존한다.

## 판정

| 대상 | 증명하려는 최소 런타임 계약 | 제외 |
|---|---|---|
| Ch06 6.4 | MoveItPy 코드의 존재하지 않는 URDF 경로를 재확인하고 BLOCKED 유지 | MoveIt 계획·실행 |
| Ch07 7.2 | 실제 이미지 3개 이상, 유효한 CameraInfo K, RSP의 camera_link → camera_optical_frame TF 수신 | RGB-D 깊이 정렬·객체 인식·GUI |
| Ch09 | 과거 12관절 명령·측정 성공 증거 보존 | 몸체 자세·접촉·넘어짐 미검증 |
| Ch10 | Issue #123 | 모든 실행 보류 |
| Ch11 | Gazebo→sim_odometry→EKF /odom 및 odom→base_footprint TF, scan/slam 데이터, SLAM lifecycle Active | 실제 자기 위치 정확도, 지도 저장·루프 폐합 |
| Ch13 | v53 기본실습 Level2·Level3 1회 PASS 원본 JSON(검사10개·무파지·외부94자산) 보존 및 Owner pending 확인 | 원격 새 환경 전체 재현, 전체 파지·운반·배치 |

선행 스크립트의 FAIL은 FAIL이다. 실패가 Gazebo 카메라 자산·렌더러·브리지·ROS QoS·Lifecycle 어느 구간인지 `stages.log`, 로그, JSON으로 구분한다. Ch10의 알려진 결함을 다른 챕터의 성공 근거로 활용하지 않는다.


## 2026-11-12 실제 공개 CI 판정

- Ch11: [실제 CI #43219759351](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43219759351), [증거 Artifact](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43219759351/artifacts/13945461995). `/odom` 105건, `/odom/raw` 100건, `/scan/slam` 5건, odom→base_footprint/map→odom TF, OccupancyGrid 138×137, slam_toolbox active. **헤드리스 EKF·TF·scan·SLAM map 발행 PASS**. 지도 저장·루프폐합·실제 위치 정밀도는 NOT_RUN.
- Ch06: MoveItPy `urdf/my_robot.urdf` 누락 [Issue #126](https://github.com/silverbjin/Pysical_AI_ROS2/issues/126), 계획·실행 **BLOCKED**.
- Ch13: v53 문서의 Level2/Level3 기본 실행 1회씩 PASS 역사 기록 보존, 새 현장 실행/Owner 사인오프 미수행.
- Ch07: `ros2 pkg`/colcon, Xacro, Gazebo entity spawn, `camera_link→camera_optical_frame` TF는 확인. 그러나 [최초 CI #43219759351](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43219759351) 및 [Xvfb 재검 #43220866643](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43220866643)에서 OGRE2 센서 렌더러 `free(): unaligned chunk detected in tcache 2` SIGABRT가 공통 재현됨. 양쪽에서 Image 0개, CameraInfo 0개, TF 1개. **Ch07 카메라 BLOCKED**, [Issue #127](https://github.com/silverbjin/Pysical_AI_ROS2/issues/127)에서 추적한다.
- renderer 실측이 불가능한 동일 공개 CI에서 세 번째 자동 반복 시도는 하지 않는다. 워크플로의 Ch07 실제 프로브는 수동 `workflow_dispatch`만으로 실행할 수 있게 유지한다. 이를 Ch07 검수 PASS라고 표시하지 않는다.
- Ch09 12관절 명령과 측정의 과거 성공을 유지하되 몸체 균형·실제 발 접촉은 **NOT_RUN**. Ch10은 사용자의 요청대로 **HOLD**.
- 최종 Owner WSL2의 실제 Gazebo/RViz 카메라 GUI/렌더러 확인은 별도 인수. 새 엔진/OS 설치나 개발 내용 변경 없이 CI 로그가 가지는 한계를 보존한다.
