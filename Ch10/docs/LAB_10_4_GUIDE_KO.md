# 10.4절 실습 가이드 — 다리 역운동학 및 FK 교차 검증

> 상태: **교육용 절차 제공**. 현재 저장소를 기준으로 작성했으나 ROS 2/Gazebo 실기동 성공은 미검증. 실행에 문제가 있는 부분은 아래 검증 게이트를 통과하기 전까지 '완료'라고 기록하지 않는다.

## 1. 목표와 배경

원고에서 요구한 FK(IK(P))의 1mm 기준은 '동일한 수학 모델 내부' 검증일 뿐, Gazebo URDF 관절 축 일치성을 자동 증명하지 않는다. IK 단독 수학 검증과 시뮬레이션 물리 검증을 두 단계로 나눈다.

원고와 코드가 다른 경우에는 원고를 무조건 실행하지 말고 소스의 실제 API·출력 타입을 확인한다. 자세한 근거는 [리뷰 보고서](SECTION_10_4_REPORT_KO.md)에 있다.

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
cd Ch10/ros2_ws
MPLBACKEND=Agg python3 test_ik.py
MPLBACKEND=Agg python3 test_ik_interactive.py
ros2 run xacro xacro src/my_quadruped_bot/urdf/robot.urdf.xacro > /tmp/ch10_robot.urdf
check_urdf /tmp/ch10_robot.urdf
```

메모: Python 라이브러리 단독 실습은 Gazebo 없이 가능한 항목이지만, GUI/ROS 명령은 해당 의존성과 화면 환경이 있어야 한다. `MPLBACKEND=Agg`는 화면 없이 수식을 실행하는 대안이며, 그림 파일을 자동 저장하는 명령은 아니다.

## 4. 관찰 항목 및 판정 기준

1. **검증 1:** 독립 3D FK와 IK의 발끝 위치 오차를 좌/우 다리별 검증한다. / PASS 기준: 측정값 또는 화면·토픽 증거 확보, 불일치 시 FAIL
2. **검증 2:** 목표가 작업공간 밖이거나 조인트 리미트를 벗어나면 정상 수행으로 판정하지 않는다. / PASS 기준: 측정값 또는 화면·토픽 증거 확보, 불일치 시 FAIL
3. **검증 3:** 기구학 수학 테스트와 URDF 일치성 검사를 각각 증거로 남긴다. / PASS 기준: 측정값 또는 화면·토픽 증거 확보, 불일치 시 FAIL

오류 또는 예상과 다른 출력이 발생하면 증상, 재현 명령, 실행 환경, 사용된 토픽/프레임, 코드 파일·라인을 기록한 뒤 변경한다. 단순 실행 완료(exit 0)를 안정적 보행의 성공으로 취급하지 않는다.

## 5. 문제 해결 및 확장 과제

1. **IK와 실제 URDF의 길이·회전 영점이 불일치:** xacro 확장→URDF joint origin/axis 추출→독립 FK로 맞춘 뒤 IK 분기/부호/offset 수정.
2. **작업공간 밖 목표를 끝점으로 클램프해 성공처럼 반환:** unreachable 신호와 projected 목표/오차를 분리하고 범위 검사.
3. **관절 한계 검사 부재:** joint limit과 FK/URDF 교차 검증을 통과하지 않으면 Gazebo 이동 실습 차단.
4. **FK 테스트가 동일 가정을 공유:** 난수 seed, 양측 미러링, 에러 분포, URDF 독립 FK, 임계치 초과 음성 사례를 추가.

## 6. 학습 증거 및 완료 조건

- [ ] 명령 및 파라미터, 코드 Git SHA, OS/ROS/Gazebo 버전 기록
- [ ] 핵심 출력·그래프·토픽 타입·단위·좌표계 기록
- [ ] 실패한 테스트의 결과도 원본 그대로 보존
- [ ] 수정 시 단위 테스트 재실행 및 다른 절과의 회귀 영향 확인
- [ ] Gazebo 관련 주장은 실제 시뮬레이션 실행과 센서/관절 실측 결과를 동반

> 주의: 수학적 궤적 또는 메시지 발행 확인만으로 실제 발 접촉·전진·낙상 방지 능력이 검증되는 것은 아니다.
