# 13.1 통합 모바일 매니퓰레이터 설계

기준 저장소: `silverbjin/Pysical_AI_ROS2`  
기준 커밋: `1451f54a64374f2ff150a39429cc89e9e3b07696`  
대상 환경: ROS 2 Jazzy, Gazebo Harmonic, MuJoCo 3.3.7, Python 3.10 이상

## 1. 목적과 완료 기준

13.1절은 4족 베이스와 6DoF 팔·평행 그리퍼를 하나의 물리 모델과 TF 트리로 결합하고, Ch13만 빌드·설치한 깨끗한 환경에서 Gazebo와 MuJoCo 중 한 엔진을 선택해 실행하는 기반 실습이다.

완료로 인정하려면 다음을 모두 만족해야 한다.

- Ch05~Ch12 원본을 수정하지 않는다.
- Ch13 내부 복사본과 명시적 외부 의존성만으로 빌드·실행한다.
- Gazebo와 MuJoCo가 동일한 링크·관절 이름, 축, 한계, 장착 변환을 사용한다.
- 다리 12개, 팔 6개, 그리퍼 2개의 총 20개 가동 관절이 이름으로 매핑된다.
- TF는 `odom -> base_footprint -> base_link -> arm_mount -> ... -> tool0`의 단일 트리이며 같은 child frame을 둘 이상의 노드가 발행하지 않는다.
- 다리·팔·그리퍼 명령은 각 그룹의 단일 생산자와 전체 명령의 단일 중재자를 거쳐 엔진에 전달된다.
- 실제 Gazebo 서버와 실제 MuJoCo `mj_step`에서 모델 로드, 상태 발행, 명령 반영, 안정적 정지, 종료를 검증한다.
- 간단한 fixture를 사용해 그리퍼가 물체에 접촉하고 물체를 들어 올린 상태를 일정 시간 유지하는지 물리 상태로 검사한다. 이는 전체 발견·접근·운반·배치 과제 성공과 구분한다.
- 실습 가이드, 재사용 명세, 변경·리뷰 보고서, 원시 로그와 기계 판독 결과를 `Ch13` 안에 남긴다.

## 2. 현재 구현 사실과 13.1 제안의 경계

### 확인된 기존 구현

- Ch11 `my_quadruped_bot`에는 Gazebo Harmonic용 12관절 4족 Xacro, 센서, 개별 관절 위치 제어 플러그인과 launch가 있다.
- Ch12 0.8.0에는 12관절 MuJoCo 보행 모델, 48차원 locomotion 정책 계약, 이름 기반 관절 정렬, 명령 제한·시각 검증·watchdog, ROS 2용 MuJoCo bridge와 Gazebo 어댑터가 있다.
- Ch12.8 증거는 짧은 2,048-transition PPO 번들로 두 엔진의 50 Hz 폐루프 연결을 검증했지만 안정적인 전진 보행이나 목표 도착을 입증하지 않았다.
- Ch08에는 6DoF 팔과 2지 그리퍼의 URDF/MJCF가 있다. 원래 모델은 링크가 길고 무거워 Ch11 베이스에 그대로 탑재하기에는 부적합하다.
- Ch06 MoveIt 설정은 5축 팔과 고정 `world -> base_link` 가정을 사용하므로 6DoF 부유 베이스 결합 모델에 그대로 적용할 수 없다.

### 이번 절에서 구현할 내용

- 축소·경량화한 교육용 6DoF 팔을 Ch11 4족 베이스에 장착한 Xacro와 동등한 MJCF.
- 두 엔진에서 공유하는 관절 목록, 그룹, 장착 변환, 안전 한계와 명령 소유권 계약.
- Gazebo 및 MuJoCo 선택형 launch, 상태 집계, 명령 중재, smoke/물리 파지 검증.
- Ch12.8의 다리 정책 계약을 Ch13 이름공간과 자원 경로로 복사·수정한 선택적 locomotion 어댑터. 기본 실행은 정책 비활성 모니터링과 기립 hold다.

### 구현했다고 주장하지 않을 내용

- MoveIt 2 planning group, IK solver, planning scene, trajectory execution.
- 하나의 `ros2_control` SystemInterface가 20개 관절을 소유하는 구조.
- 충분히 학습된 PPO의 안정 보행, 팔 적재 보행, whole-body control.
- RGB-D 인식, Nav2 접근, 전체 pick-and-place 상태 머신, 실제 로봇 배포.

원고의 MoveIt 2, 통합 ros2_control, Lifecycle, PPO 안정성 설명은 이 절의 목표 아키텍처 또는 후속 절 제안으로 표시하며, 실행 검증된 현재 기능처럼 서술하지 않는다.

## 3. 선택한 구조와 대안

### 선택: 공통 계약 + 엔진별 어댑터

`ch13_sim_core`가 관절·프레임·명령 그룹과 MuJoCo 모델을 소유한다. ROS 패키지 `ch13_robot_description`은 결합 Xacro·Gazebo 자원·robot_state_publisher launch를, `ch13_control`은 명령 중재·상태 검증·엔진 bridge를 소유한다. 두 엔진은 동시에 같은 ROS domain에서 실행하지 않는다.

이 구조는 Ch12.8의 이름 기반 정책 계약을 보존하면서 팔과 그리퍼를 별도 제어 그룹으로 추가할 수 있고, Gazebo 플러그인과 MuJoCo actuator 배열 차이를 backend 경계 안에 가둔다.

### 검토했으나 선택하지 않은 대안

1. **Ch11과 Ch12를 런타임 의존성으로 source**: 구현량은 적지만 Ch13 단독 빌드 조건을 위반한다.
2. **13.1에서 MoveIt 2와 ros2_control까지 완성**: 목표 아키텍처에는 가깝지만 기존 5축 SRDF를 재설계하고 두 엔진 하드웨어 인터페이스를 함께 검증해야 하므로 13.1 모델 통합의 범위를 넘는다.
3. **Gazebo와 MuJoCo를 한 launch에서 동시에 실행**: 비교에는 편리하지만 `/clock`, TF, joint state와 명령 소유권이 충돌한다.

## 4. 패키지와 파일 경계

```text
Ch13/
  README.md
  pyproject.toml
  src/ch13_sim_core/
    contract.py
    command.py
    mujoco_bridge_core.py
    models/integrated_robot.xml
  ros2_ws/src/
    ch13_robot_description/
      urdf/{integrated_robot,quadruped_base,arm_6dof}.urdf.xacro
      config/{ros_gz_bridge,joint_contract}.yaml
      worlds/mobile_manipulation.sdf
      launch/display.launch.py
    ch13_control/
      ch13_control/{command_arbiter,state_monitor,mujoco_bridge,gazebo_router}.py
      launch/mobile_manipulation.launch.py
  config/
  scripts/
  tests/
  docs/
    LAB_13_1_GUIDE_KO.md
    REUSE_MANIFEST.md
    CHANGE_REPORT_KO.md
  evidence/
```

ROS 패키지는 필요한 자원만 설치하고 Ch05~Ch12의 `install/`, `build/`, `log/` 또는 Python 경로를 참조하지 않는다. `colcon build`는 `Ch13/ros2_ws`에서 수행한다.

## 5. 결합 모델

### 링크와 좌표계

- REP-103 기준: +X 전방, +Y 좌측, +Z 상방, 회전은 rad.
- Ch11 몸체 크기 0.60 × 0.30 × 0.15 m와 다리 링크 길이·질량·축·한계를 유지한다.
- 팔 장착 변환은 `base_link -> arm_mount` 고정 관절 하나로 표현한다. 기본 위치는 몸체 중앙보다 뒤쪽 `(-0.10, 0, 0.095) m`이며, 실제 collision과 질량중심 검증 결과에 따라 한 번만 조정한다.
- Ch08의 Z-Y-Y-X-Y-Z 6축 순서를 유지하되 관절 이름은 `arm_joint_1`~`arm_joint_6`으로 구분한다.
- 팔 링크 길이와 질량은 4족 플랫폼에 맞게 축소한다. 장착판·팔·그리퍼의 질량과 관성을 시각 형상과 일관되게 계산한다.
- TCP는 `tool0`, 물리 파지 기준점은 `grasp_site`로 고정한다.

### 관절 계약

- 다리: `fr`, `fl`, `rr`, `rl` 순서, 각 `hip`, `thigh`, `calf` 순서의 12개.
- 팔: `arm_joint_1`~`arm_joint_6` 6개.
- 그리퍼: `gripper_left_joint`, `gripper_right_joint` 2개.
- 따라서 원고의 “총 18개 모터”는 다리와 팔의 주 관절 수이며, 물리 그리퍼까지 포함한 가동 관절·actuator 수는 20개라고 교정한다.
- URDF와 MJCF의 축, 한계, 기본 자세, actuator 이름을 자동 비교한다. actuator index를 상수 위치로 가정하지 않고 이름으로 찾는다.

## 6. 상태와 명령 소유권

### 상태

- 각 엔진 bridge가 `/ch13/joint_states_raw`의 유일한 발행자다.
- 상태 집계 노드는 이름·중복·누락·NaN·시각 역행을 검사하고 완전한 20관절 상태만 `/joint_states`로 발행한다.
- Gazebo odometry가 `odom -> base_footprint` 동적 TF를 소유하고 robot_state_publisher가 `base_footprint` 아래 TF를 소유한다. MuJoCo bridge도 같은 경계를 지킨다.

### 명령

```text
leg producer      -> /ch13/command/legs     (12)
arm producer      -> /ch13/command/arm      (6)
gripper producer  -> /ch13/command/gripper  (2)
                         |
                  command_arbiter
                         |
                 /ch13/command/actuators    (20, sole publisher)
                         |
           mujoco_bridge OR gazebo_router
```

- 모든 메시지는 joint name과 stamp를 포함한다.
- 중재기는 그룹별 허용 이름, 중복 publisher, 값의 유한성, 관절 한계, 명령 만료를 검사한다.
- 다리는 Ch12.8 정책 또는 기립 hold 중 하나, 팔은 demo/후속 MoveIt 실행기 중 하나만 소유한다.
- 조작 중 다리 명령 기본값은 영토크가 아니라 검증된 기립 위치 hold다.
- stale arm/gripper 명령은 마지막 안전 위치를 hold하고 진단 상태를 발행한다.

## 7. 물리 검증 시나리오

### 정적·계약 검증

- Xacro 전개와 MJCF 로드.
- 단일 TF 루트, 중복 링크·관절 없음.
- 20개 관절과 actuator의 이름·축·한계·그룹 일치.
- 각 명령 토픽의 publisher 충돌과 잘못된 그룹 관절 거부.
- Ch13 설치 후 import와 ROS package prefix가 Ch13 설치 경로를 가리키는지 확인.

### MuJoCo

- 실제 `mj_step`으로 기립 자세 안정화.
- 다리를 hold한 채 팔 각 관절에 작은 왕복 명령을 주고 base 높이·기울기·유한 상태를 기록.
- fixture 물체에서 양 손가락 접촉 후 팔을 들어 물체 높이가 임계값 이상 증가하고 상대 위치가 유지되는지 검사.
- 잘못된·오래된·역순 명령 거부와 정상 close를 검사.

### Gazebo

- 실제 headless Gazebo Harmonic 서버에서 결합 로봇과 물체 spawn.
- 20관절 상태, TF, odometry와 simulation clock 진행을 검사.
- 다리 hold 상태에서 팔·그리퍼 명령 반영과 base 안정성을 확인.
- 가능한 동일 fixture 파지·들기 검사를 수행한다. Gazebo에서 신뢰할 수 있는 접촉/물체 pose 관측을 제공하지 못하면 이를 실패 또는 미검증으로 기록하며 MuJoCo 결과로 대체하지 않는다.
- `/server_control` 응답, 강제 종료 여부, 남은 프로세스를 기록한다.

## 8. TDD와 증거

구현은 관절·TF·명령 계약 테스트를 먼저 실패시키고 최소 구현으로 통과시키는 순서로 진행한다. 물리 결함은 재현 가능한 시드·초기 pose·수치 임계값을 가진 회귀 테스트로 남긴다.

`Ch13/evidence/`에는 다음을 저장한다.

- 기준/최종 commit, 작업트리 상태와 앞 장 무변경 diff.
- Python·ROS·Gazebo·MuJoCo 버전과 설치 로그.
- RED/GREEN 단위 테스트 로그와 전체 테스트 로그.
- 각 엔진의 launch 로그, 기계 판독 `result.json`, 대표 프레임.
- 관절·TF·publisher 목록, base/object pose, 접촉·파지 유지, 종료 결과.
- 의도한 실패 검사와 최종 성공 결과를 서로 다른 경로에 보존한다.

## 9. 문서와 재사용 추적

`REUSE_MANIFEST.md`에는 기준 커밋, 원래 경로, Ch13 새 경로, 변경 이유, 라이선스와 해시를 기록한다. 주요 후보는 다음과 같다.

- Ch11 4족 Xacro·Gazebo world/bridge.
- Ch12 `ros_core.py`, ROS controller/bridge의 검증된 안전 계약.
- Ch08 6DoF 축 배열과 그리퍼 형상·접촉 설정.

초안·오류·백업 접미 파일은 실행 경로에 복사하지 않는다. 기존 장 파일은 최종 diff에서 변경이 없어야 한다.

## 10. 인수 범위와 한계 표현

13.1 완료는 “통합 모델과 엔진별 명령·상태 경로가 실행됐다”는 뜻이다. 제한된 fixture 파지가 통과해도 물체 발견, 접근, 일반 IK, collision-aware 경로 계획, 운반·배치 성공을 뜻하지 않는다. 짧은 PPO 번들이 연결 검증을 통과해도 안정 보행이나 팔 하중 강건성을 뜻하지 않는다. 실행하지 못한 GUI, MoveIt, ros2_control, 실제 로봇 검증은 보고서에 미검증으로 명시한다.
