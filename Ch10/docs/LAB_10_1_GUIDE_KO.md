# 10.1절 실습 가이드 — 보행 제어 개요와 노드 구조

> 상태: **교육용 절차 제공**. 현재 저장소를 기준으로 작성했으나 ROS 2/Gazebo 실기동 성공은 미검증. 실행에 문제가 있는 부분은 아래 검증 게이트를 통과하기 전까지 '완료'라고 기록하지 않는다.

## 1. 목표와 배경

10.1은 실제 보행 성공 판정이 아니라 `/cmd_vel → 보행계획 → 궤적 → IK → 12개 위치 지령 → Gazebo` 계약 이해가 목표다. 원고의 50 Hz 골격과 현행 `quadruped_controller.py`의 100 Hz, `quadruped_controller_ros2.py`의 50 Hz를 구분한다.

원고와 코드가 다른 경우에는 원고를 무조건 실행하지 말고 소스의 실제 API·출력 타입을 확인한다. 자세한 근거는 [리뷰 보고서](SECTION_10_1_REPORT_KO.md)에 있다.

## 2. 실습 환경 준비

Ubuntu 24.04/ROS 2 Jazzy/Gazebo Harmonic을 권장한다. 본 경로가 Ch10 패키지이며 **Ch09/Ch11 등 다른 워크스페이스의 install을 먼저 source하지 않는다**.

```bash
git clone https://github.com/silverbjin/Pysical_AI_ROS2.git
cd Pysical_AI_ROS2
source /opt/ros/jazzy/setup.bash
sudo apt update
sudo apt install -y python3-numpy python3-matplotlib python3-colcon-common-extensions python3-rosdep
cd Ch10/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
python3 -m compileall -q src/my_quadruped_bot/my_quadruped_bot
```

필요한 ROS/Gazebo 패키지가 없다면 환경 구성 후 다시 수행한다. `rosdep` 오류가 나거나 패키지 경로가 Ch10 외부를 가리키면 그 결과를 먼저 해결한다. 기존 워크스페이스의 자동 source를 해제한 새 터미널에서 실행할 것을 권장한다.

## 3. 절별 따라하기

```bash
ros2 pkg executables my_quadruped_bot
ros2 topic list -t | grep -E 'cmd_vel|joint/.*/cmd_pos|joint_states'
ros2 node list
```

메모: Python 라이브러리 단독 실습은 Gazebo 없이 가능한 항목이지만, GUI/ROS 명령은 해당 의존성과 화면 환경이 있어야 한다. `MPLBACKEND=Agg`는 화면 없이 수식을 실행하는 대안이며, 그림 파일을 자동 저장하는 명령은 아니다.

## 4. 관찰 항목 및 판정 기준

1. **검증 1:** 실제 실행 파일(`setup.py` console_scripts)과 원고 내 가상 이름의 차이를 식별한다. / PASS 기준: 측정값 또는 화면·토픽 증거 확보, 불일치 시 FAIL
2. **검증 2:** 실제 브리지의 12개 Float64 명령 토픽을 확인한다. / PASS 기준: 측정값 또는 화면·토픽 증거 확보, 불일치 시 FAIL
3. **검증 3:** URDF 치수·각도 영점이 코드와 다른 점을 표로 기록한다. / PASS 기준: 측정값 또는 화면·토픽 증거 확보, 불일치 시 FAIL

오류 또는 예상과 다른 출력이 발생하면 증상, 재현 명령, 실행 환경, 사용된 토픽/프레임, 코드 파일·라인을 기록한 뒤 변경한다. 단순 실행 완료(exit 0)를 안정적 보행의 성공으로 취급하지 않는다.

## 5. 문제 해결 및 확장 과제

1. **제어기 진입점·실제 메시지 계약이 원고 골격과 다름:** 실습 시작 전에 실제 인터페이스를 도식화하고 `ros2 topic info`로 타입·발행자 수를 확인한다.
2. **URDF-제어기 기구학 기준 불일치:** 실제 URDF/Xacro FK와 IK를 같은 기하·관절 영점/축으로 통일한다.
3. **컨트롤러가 여러 개 존재하며 동시에 구동하면 명령 충돌:** 제어권 1개만 활성화하고 나머지는 종료한다.
4. **패키지 의존성 선언 미비:** rosdep/manifest 의존성 점검 후 환경별 빌드 검증.

## 6. 학습 증거 및 완료 조건

- [ ] 명령 및 파라미터, 코드 Git SHA, OS/ROS/Gazebo 버전 기록
- [ ] 핵심 출력·그래프·토픽 타입·단위·좌표계 기록
- [ ] 실패한 테스트의 결과도 원본 그대로 보존
- [ ] 수정 시 단위 테스트 재실행 및 다른 절과의 회귀 영향 확인
- [ ] Gazebo 관련 주장은 실제 시뮬레이션 실행과 센서/관절 실측 결과를 동반

> 주의: 수학적 궤적 또는 메시지 발행 확인만으로 실제 발 접촉·전진·낙상 방지 능력이 검증되는 것은 아니다.
