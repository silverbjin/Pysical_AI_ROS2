# 10.2절 실습 가이드 — 보행 계획기: 위상과 듀티 팩터

> 상태: **교육용 절차 제공**. 현재 저장소를 기준으로 작성했으나 ROS 2/Gazebo 실기동 성공은 미검증. 실행에 문제가 있는 부분은 아래 검증 게이트를 통과하기 전까지 '완료'라고 기록하지 않는다.

## 1. 목표와 배경

FL/RR 대각선 위상과 FR/RL 위상 차 0.5, trot duty=0.5의 뜻과 `walk`·`pace` 오프셋을 관찰한다. 10.2절 단계에서는 물리 접촉 성공을 보장하지 않는다.

원고와 코드가 다른 경우에는 원고를 무조건 실행하지 말고 소스의 실제 API·출력 타입을 확인한다. 자세한 근거는 [리뷰 보고서](SECTION_10_2_REPORT_KO.md)에 있다.

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
PYTHONPATH=src/my_quadruped_bot python3 - <<'PY'
from my_quadruped_bot.gait_planner import GaitPlanner
p = GaitPlanner('trot', 0.5)
for t in [0.0, 0.125, 0.25, 0.375]:
    p.current_time = t
    print(t, p.get_leg_states())
PY
```

메모: Python 라이브러리 단독 실습은 Gazebo 없이 가능한 항목이지만, GUI/ROS 명령은 해당 의존성과 화면 환경이 있어야 한다. `MPLBACKEND=Agg`는 화면 없이 수식을 실행하는 대안이며, 그림 파일을 자동 저장하는 명령은 아니다.

## 4. 관찰 항목 및 판정 기준

1. **검증 1:** 같은 시각에 FL과 RR의 위상·상태가 일치한다. / PASS 기준: 측정값 또는 화면·토픽 증거 확보, 불일치 시 FAIL
2. **검증 2:** FR과 RL의 위상·상태가 일치하고 반대 대각선 그룹과 0.5 주기 차이가 난다. / PASS 기준: 측정값 또는 화면·토픽 증거 확보, 불일치 시 FAIL
3. **검증 3:** 스윙/스탠스 경계에서 phase가 0부터 다시 시작함을 설명한다. / PASS 기준: 측정값 또는 화면·토픽 증거 확보, 불일치 시 FAIL

오류 또는 예상과 다른 출력이 발생하면 증상, 재현 명령, 실행 환경, 사용된 토픽/프레임, 코드 파일·라인을 기록한 뒤 변경한다. 단순 실행 완료(exit 0)를 안정적 보행의 성공으로 취급하지 않는다.

## 5. 문제 해결 및 확장 과제

1. **실행 진입점 오류:** `ros2 run my_quadruped_bot gait_planner`를 실행 예제로 제시하지 말고 Python 모듈로 임포트한다. 필요하면 별도 CLI 구현.
2. **시간 래핑은 단일 주기만 감산:** 주기 경계, 큰 dt, 0/음수 dt, 초과 범위 입력을 테스트한다.
3. **상태 반환 계약 혼동:** `is_swing=False`를 stance로 해석하고 호출부를 현행 API로 맞춘다.
4. **FSM 테스트는 검증력이 부족:** 테스트를 불변식 기반 assert로 교체하고 미끄럼/전이 시점 회귀 검사.

## 6. 학습 증거 및 완료 조건

- [ ] 명령 및 파라미터, 코드 Git SHA, OS/ROS/Gazebo 버전 기록
- [ ] 핵심 출력·그래프·토픽 타입·단위·좌표계 기록
- [ ] 실패한 테스트의 결과도 원본 그대로 보존
- [ ] 수정 시 단위 테스트 재실행 및 다른 절과의 회귀 영향 확인
- [ ] Gazebo 관련 주장은 실제 시뮬레이션 실행과 센서/관절 실측 결과를 동반

> 주의: 수학적 궤적 또는 메시지 발행 확인만으로 실제 발 접촉·전진·낙상 방지 능력이 검증되는 것은 아니다.
