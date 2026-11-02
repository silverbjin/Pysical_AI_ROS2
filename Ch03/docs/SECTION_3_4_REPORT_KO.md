# SECTION 3.4 — Gazebo Harmonic 환경 및 SDF 월드 리뷰

- 원고: 3.4.1~3.4.4 (버전, 설치, GUI, world SDF)
- 대상: `Ch03/ros2_ws/src/my_robot_description/worlds/my_world.sdf`
- 기준: `main@9aafa9538352cc01f5e0154ad621f1200a27b0ef`, 2026-10-20
- 결론: **정적 검토 / 코드 수정 불필요 / Gazebo 실행 미검증**

## 확인 사항
SDF 최상위는 `<sdf version="1.8">`, 월드 이름은 **`my_first_world`**이다. 1ms `max_step_size`, `real_time_factor=1.0`, Physics·UserCommands·SceneBroadcaster·Sensors(ogre2) 시스템 플러그인, directional sun, ground_plane(static, collision plane)이 정의돼 있다. 해당 소스에는 원고에 나타난 비표준 XML 주석 `<!—`가 **존재하지 않으며**, 표준 `<!-- ... -->`를 사용한다.

## 위험·경고
| ID | 심각도 | 내용 | 조치 |
|---|---|---|---|
| 3.4-01 | Medium | 원고의 `gz sim` 무인자 실행은 원하는 `my_world.sdf`를 지정하지 않음 | `gz sim -v 4 -r <월드파일>` 권장 |
| 3.4-02 | Medium | 빈 월드/기본 월드와 본 장의 `my_first_world` 이름을 혼용하면 joint state 브리지 경로 오류 | `gz topic -l`과 실제 월드 이름 확인 |
| 3.4-03 | Low | WSL2/WSLg ogre2에서 GUI 렌더러 장애 가능 | GUI 실패와 물리 서버 실패를 별도로 진단 |
| 3.4-04 | Info | `real_time_factor`는 설정 목표, 실제 RTF=1.0의 보증이 아님 | `gz stats` 측정값으로 구분 |

## 정적 확인 vs 실행
- **PASS(소스 리뷰)**: world 이름, 바닥의 정적 정의, 플러그인 종류 및 파일 경로 점검.
- **NOT RUN**: `gz sim`, `gz sdf -k`, `gz stats`, GUI/OGRE 렌더링, 물리 업데이트. ROS 2/Gazebo 부재.

## 실제 검증 명령
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
sudo apt install -y ros-jazzy-ros-gz
gz sim -v 4 -r src/my_robot_description/worlds/my_world.sdf
# 다른 터미널
gz topic -l
gz stats
```
성공: world=`my_first_world`, 바닥·빛 표시, Physics/UserCommands/SceneBroadcaster 로딩 실패 없음, sim-time 증가. 실패하면 ROS/WSLg/Gazebo 로그 및 환경변수 `GZ_SIM_RESOURCE_PATH` 점검. Acceptance=`PENDING_RUNTIME_VERIFICATION`.
