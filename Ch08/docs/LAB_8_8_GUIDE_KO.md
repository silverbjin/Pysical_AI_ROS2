# LAB 8.8 — Sim-to-Real의 제어 계약과 ROS 2 격리 검증

**목표:** 학습 정책을 실제 하드웨어에 곧바로 투입하지 않고, **정규화 action → 단위·관절 매핑 확인 → 안전 차단 → 시뮬레이션**의 순서를 설계한다. 원고의 랜덤화·노이즈·저역통과·E-stop 개념을 구현 현황과 분리한다.

## A. 사전 검토 — 브리지 계약 명세
다음 항목을 표로 작성하라: 정책 모델 입력 차원(현재 18), 관측 순서(`qpos6,qvel6,ee3,target3`), 행동 차원(6), XML actuator gear(50,50,30,10,5,2), MuJoCo 물리 timestep(0.002s), policy 주기(5 step = 0.01s). ROS의 `Float64` position 명령과 MuJoCo motor ctrl은 물리량이 다르므로 **값을 그대로 복사하면 안 된다.**

## B. 원리 실습 — 안전 필터를 오프라인 배열로 테스트
아래는 로봇 제어가 아닌 순수 Python 수치 데모다. 실제 actuator에 publish하지 않는다.

```bash
python - <<'PY'
import numpy as np
prev=np.zeros(6)
alpha=0.2
for raw in (np.array([2.,-2.,.5,0,0,0]),np.array([-2.,2.,0.,0.,0.,0.])):
    bounded=np.clip(raw,-1.,1.)
    filtered=alpha*bounded+(1-alpha)*prev
    print("raw",raw,"bounded",bounded,"filtered",np.round(filtered,3))
    assert np.max(np.abs(filtered))<=1.
    prev=filtered
PY
```

차단 기준: NaN/Inf, 관측 시각 만료, joint limits 불일치, 모델 차원 불일치, 비상정지 상태. 소프트웨어 클립은 보호 계층 하나일 뿐 물리 E-stop을 대체하지 못한다.

## C. MuJoCo 도메인 랜덤화 설계 과제
- `env.model.body_mass`, `geom_friction`, `dof_damping`의 **원본 배열을 생성자에서 단 한 번 저장**한다.
- 매 `reset(seed)`마다 원본에 대해 랜덤 배율을 적용하고, 관련 엔진 재계산 필요 항목을 MuJoCo 버전 문서에 따라 확인한다.
- 샘플 로그에 원본 질량·적용 질량·시드·최소/최대 배율을 저장한다.
- 노이즈는 `self.np_random.normal`, 행동 지연은 고정 길이 deque 기반 테스트를 설계한다.
- **현재 `rl_env.py`에는 이 모델 랜덤화와 지연 큐가 없다.** 원고 코드 조각을 그대로 적용하기 전에 독립 단위 테스트를 작성한다.

## D. ROS 2 Gazebo 데모(선택, PPO 연동 아님)
ROS 2 Jazzy/Harmonic이 준비된 **새 쉘**에서만 아래를 실행한다. 이 launch는 `two_dof_arm` 데모이며 학습된 6DOF policy와 무관하다.

```bash
# ROS 2 전용 셸: Python venv 비활성화
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch08/ros2_ws
colcon build --packages-select my_robot_description --symlink-install
source install/setup.bash
ros2 pkg prefix my_robot_description
ros2 launch my_robot_description sim_sync.launch.py
```
다른 터미널에서 `ros2 topic list | grep -E 'joint|clock'`을 확인한다. `simple_arm_teleop`는 joint1/2 명령을 생성하지만 bridge에는 joint2만 지정되어 있으므로 joint1이 실제 전달된다고 가정하지 않는다. Gazebo 실행의 성공은 **이 문서를 작성할 때 검증하지 않았다.**

## E. 결과·평가
(1) 18/6 관측·행동 계약 문서, (2) 안전 필터 numeric 출력, (3) model 원본 스냅샷 및 난수 정책, (4) Gazebo 토픽 연결 현황과 불일치 목록, (5) '실기 배포 금지' 체크리스트를 작성한다. 하드웨어 구동 시험은 이 실습의 범위 밖이다.

**통과 조건:** 수치 필터 안전 범위 테스트 완료, model/ROS 메시지 의미의 불일치 지적, 하드웨어 통합에 앞선 검증 단계 3개 제시. 런타임이 불가능한 부분은 미검증으로 표시.

[리뷰 보고서](SECTION_8_8_REPORT_KO.md)
