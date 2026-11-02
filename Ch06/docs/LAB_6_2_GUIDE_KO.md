# 6.2절 실습 가이드 — KDL과 플래너를 분리해서 검사하기

> 기준: 2026-10-20 KST · GitHub main 1b9e8215e213 · 원고 6.2절 · ROS 2 Jazzy / Ubuntu 24.04 기준
> 범위: 저장소 소스 및 원고 정적 검토. 현재 세션에 ROS 2/Gazebo 실행 환경이 없으므로 실제 빌드·GUI·물리 시뮬레이션 결과는 **미검증**이다. 성공·PASS를 추정하지 않는다.
> 검토 대상: https://github.com/silverbjin/Pysical_AI_ROS2/tree/1b9e8215e2130c492969bb0da52a82e707c3a16f/Ch06

## 학습 목표
MoveIt의 `move_group`, 로봇 모델/Planning Scene, IK 플러그인, OMPL 경로 계획을 분리하여 이해한다. '해를 찾는다'와 '안전한 경로를 실행한다'를 구별한다.

## 준비
```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 pkg prefix my_robot_moveit_config
ros2 pkg prefix moveit_kinematics
ros2 pkg prefix trac_ik_kinematics_plugin  # 미설치 시 prefix 조회 실패
cat src/my_robot_moveit_config/config/kinematics.yaml
```
Trac-IK는 필요한 경우 `sudo apt install ros-jazzy-trac-ik-kinematics-plugin`로 설치한다. 설치만으로 사용 솔버가 변경되지는 않는다.

## 실습 A — 구성 읽기
1. `kinematics.yaml`의 `arm_group`과 KDL, timeout 0.005s를 찾는다.
2. `my_robot.srdf`의 arm_group 구동 관절 5개와 `link_wrist`를 표시한다.
3. `ompl_planning.yaml`에서 RRTConnect 설정의 실제 이름을 확인한다. 변경 전에 원본 YAML과 로그를 남긴다.

## 실습 B — 공정 비교
- 실습 환경이 정상 실행되는 **후속 절의 오류를 우선 해결한 뒤**, KDL 기본값으로 포즈/시드/시행 시간을 고정하여 20회 이상의 IK 결과를 수집한다.
- 선택 확장: Trac-IK 플러그인 이름을 `trac_ik_kinematics_plugin/TRAC_IKKinematicsPlugin`으로 바꾸고 같은 포즈·시드·timeout으로 반복한다. 인스턴스와 로그에 플러그인 로드가 성공했는지 확인한다.
- 두 설정 모두 실패한다면 `position_only_ik: true`(KDL 지원 여부/작업 요구에 맞게) 또는 목표 자세와 충돌 조건을 검토한다. 무조건 timeout만 늘리는 방식은 피한다.
- 계획 성공률과 물리 실행 성공률을 **별도 열**로 측정한다.

## 평가표
| 항목 | 기록 예 |
|---|---|
| Solver | KDL / Trac-IK 및 설치 버전 |
| IK | 목표 개수·성공 횟수·위치 오차·자세 오차 |
| 시간 | median, P95(ms), timeout(ms) |
| 계획 | RRTConnect planner_id·충돌 유무 |
| 결론 | 어떤 환경에서 어떤 조건이 효과적이었는가 |

**주의:** 실측 없이 'Trac-IK는 99.9% 성공' 또는 'MoveIt이 곧 최단 경로를 보장'한다고 판단하지 않는다. 참고: [보고서](SECTION_6_2_REPORT_KO.md).
