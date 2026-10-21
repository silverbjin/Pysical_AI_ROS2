# 9.5절 코드 리뷰 — 시뮬레이션 론치·스폰·TF 검증

- 검토일: **2026-10-21 (KST)** · 기준 main `bab76f6ca7df0bda6efd8882c1a698561707e51d`
- 원고: 9.5 「9.5 론치 파일 작성 및 로봇 스폰」
- 결론: **정적 검토 완료, ROS 2·Gazebo 런타임 NOT_RUN, 코드 실행 가능성 미인증**
- 범위: 요청된 리뷰/실습 문서만 추가하며 기존 소스는 수정하지 않음

## 검토한 실제 소스

- `Ch09/ros2_ws/src/my_quadruped_bot/launch/simulation.launch.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/launch/9-5_simulation.launch.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/launch/display.launch.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/config/ros_gz_bridge.yaml`
- `Ch09/ros2_ws/src/my_quadruped_bot/package.xml`
- `Ch09/ros2_ws/src/my_quadruped_bot/setup.py`

## 발견 사항

| 심각도 | 실제 코드 관찰 | 문제·개선 권고 |
|---|---|---|
| 높음 | simulation.launch.py가 robot_state_publisher에 robot_description만 전달하며 use_sim_time을 지정하지 않음 | /clock 브리지는 존재하나 ROS 노드 시간은 시스템 시간을 사용할 수 있음. use_sim_time:=true 명시 권고 |
| 확인 | 9-5_simulation.launch.py는 use_sim_time LaunchArgument를 선언해 RSP에 전달 | 같은 장의 두 런치가 시간 설정에서 다른 동작. 학습용 표준 런치 1개를 확정 권고 |
| 주의 | 9-5_simulation.launch.py는 Command(['xacro ', xacro_file])를 robot_description에 직접 전달 | 버전·실행환경에서 Launch가 XML을 잘못 타입 변환하지 않는지 확인. ParameterValue(..., value_type=str) 형태 권고 |
| 높음 | display.launch.py의 RViz 파일은 Ch09가 아니라 my_robot_description 패키지에서 검색 | Ch09 단독 실행 불가능할 수 있으므로 Ch09의 rviz/display.rviz를 참조하도록 수정 권고 |
| 높음 | package.xml에는 <depend>xacro</depend> 외 ros_gz_sim, ros_gz_bridge, robot_state_publisher, std_msgs 등 실행 의존성이 누락 | README/rosdep에서 설치 가능한 정확한 exec_depend 선언 필요 |
| 주의 | ros_gz_sim create와 robot_state_publisher가 같은 LaunchDescription에 병렬 배치 | robot_description 토픽 준비/서비스 타임아웃·스폰 성공 로그 확인, 이벤트 의존성 도입 검토 |

## 리뷰 절차와 실행 검증의 구분

- **정적 리뷰:** 원격 GitHub main의 파일 전문과 첨부 원고를 대조하여 명칭, 값, 토픽·의존성·실행 흐름의 논리 문제를 확인했다.
- **NOT_RUN:** 이 환경에는 실제 ROS 2 Jazzy / Gazebo Harmonic 시뮬레이터가 준비되어 있지 않다. `colcon build`, `colcon test`, GUI, 브리지 통신, 관절 동작·물리 기립, WSL2 화면을 실행하지 않았다.
- **검증 보류:** 원격에서 읽은 파일이 XML·Python 구문상 무오류임을 `xacro`나 ROS 런타임 결과로 확인한 것은 아니다. 아래 기대는 가이드에 있는 사용자의 실행 결과로 검증해야 한다.

## 검증 수용 기준 및 재현 지점

1. 동일 워크스페이스에서 simulation vs 9-5_simulation의 use_sim_time 값 차이는?
2. create가 실제 로봇을 스폰했는가? 이름과 월드를 확인했는가?
3. base_footprint에서 모든 4개 발까지 TF가 연결되는가?
4. Ch09 단독 source에서 RViz 설정 파일을 찾을 수 있는가?

**통과 기준:** Gazebo 스폰 로그, /joint_states, /clock, TF 및 시간 설정을 각각 별개로 확인해야 한다. GUI에 로봇이 보인다는 사실 하나로 PASS로 처리하지 않는다.

## 원고·교재 수정 및 후속 구현 권고

원고의 경로·launch 명칭·ROS 파라미터를 현재 두 런치의 차이와 비교해야 한다. ROS 시간 true 설정이 기본 simulation 런치에 자동 적용된다고 가정하지 않는다.

실제 코드 변경은 별도 승인된 수정 작업에서 담당하도록 남긴다. 수정 후에 같은 명령으로 RED→GREEN, 빌드·runtime·Evidence를 남겨야 한다. [실습 가이드](LAB_9_5_GUIDE_KO.md) · [Ch09 원본](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09).
