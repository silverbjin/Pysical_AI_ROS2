# 10.3절 실습 가이드 — 발끝 궤적과 착지점 생성

> 상태: **교육용 절차 제공**. 현재 저장소를 기준으로 작성했으나 ROS 2/Gazebo 실기동 성공은 미검증. 실행에 문제가 있는 부분은 아래 검증 게이트를 통과하기 전까지 '완료'라고 기록하지 않는다.

## 1. 목표와 배경

스탠스 상대운동과 스윙의 시작·정점·끝을 x-z 그래프로 비교하며 접지 연속성을 실험한다. 수평 보간은 `s - sin(2πs)/(2π)`, 수직 오프셋은 현행 코드의 두 구간식이다.

원고와 코드가 다른 경우에는 원고를 무조건 실행하지 말고 소스의 실제 API·출력 타입을 확인한다. 자세한 근거는 [리뷰 보고서](SECTION_10_3_REPORT_KO.md)에 있다.

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
MPLBACKEND=Agg python3 test_trajectory.py
PYTHONPATH=src/my_quadruped_bot python3 - <<'PY'
import numpy as np
from my_quadruped_bot.trajectory_generator import TrajectoryGenerator
g=TrajectoryGenerator(step_height=0.05)
a=np.array([0.,0.,-0.30]); b=np.array([0.10,0.,-0.30])
for s in (0.,0.25,0.5,0.75,1.):
    print(s, g.generate_swing(a,b,s))
PY
```

메모: Python 라이브러리 단독 실습은 Gazebo 없이 가능한 항목이지만, GUI/ROS 명령은 해당 의존성과 화면 환경이 있어야 한다. `MPLBACKEND=Agg`는 화면 없이 수식을 실행하는 대안이며, 그림 파일을 자동 저장하는 명령은 아니다.

## 4. 관찰 항목 및 판정 기준

1. **검증 1:** 시작·끝 위치는 지정된 좌표와 맞고 최고점은 기준 z + step_height이다. / PASS 기준: 측정값 또는 화면·토픽 증거 확보, 불일치 시 FAIL
2. **검증 2:** 같은 인수로 실행할 때 출력이 재현된다. / PASS 기준: 측정값 또는 화면·토픽 증거 확보, 불일치 시 FAIL
3. **검증 3:** 그래프는 궤적만 검증하고 Gazebo 접촉·전진 성공의 증거가 아님을 구분한다. / PASS 기준: 측정값 또는 화면·토픽 증거 확보, 불일치 시 FAIL

오류 또는 예상과 다른 출력이 발생하면 증상, 재현 명령, 실행 환경, 사용된 토픽/프레임, 코드 파일·라인을 기록한 뒤 변경한다. 단순 실행 완료(exit 0)를 안정적 보행의 성공으로 취급하지 않는다.

## 5. 문제 해결 및 확장 과제

1. **궤적 통합 API가 gait 설정을 무시:** 현행 planner의 frequency와 duty를 명시적으로 주입해 동일한 시간 기준을 사용.
2. **yaw를 선속도 벡터의 Z성분처럼 전달:** 회전 명령은 leg별 원운동 접선 속도로 변환하고 z 속도는 0으로 유지.
3. **좌표계 설명과 명목 위치 차이:** body→hip 변환 계약과 힙 오프셋의 단일 출처 명시.
4. **배열 입력의 불변성·속도 평활 확인 필요:** np.ndarray 유효성, 양 끝 위치/수평·수직 속도, 최고점, 입력변형 여부를 수치 검증.

## 6. 학습 증거 및 완료 조건

- [ ] 명령 및 파라미터, 코드 Git SHA, OS/ROS/Gazebo 버전 기록
- [ ] 핵심 출력·그래프·토픽 타입·단위·좌표계 기록
- [ ] 실패한 테스트의 결과도 원본 그대로 보존
- [ ] 수정 시 단위 테스트 재실행 및 다른 절과의 회귀 영향 확인
- [ ] Gazebo 관련 주장은 실제 시뮬레이션 실행과 센서/관절 실측 결과를 동반

> 주의: 수학적 궤적 또는 메시지 발행 확인만으로 실제 발 접촉·전진·낙상 방지 능력이 검증되는 것은 아니다.
