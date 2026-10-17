# 12.7 구현·교정 및 실행 결과

검증일: 2026-10-17. 기본 환경은 기존 `QuadrupedLocomotionEnv`이며, goal/avoidance도 동일한 wrapper로 지원한다. 기존 환경 클래스의 동작이나 관측 차원은 변경하지 않았다.

## 원고에서 교정한 부분

- 전체 `body_mass` 배열을 변경하는 대신 base_link 아래 동적 로봇 링크만 골라 질량·관성을 같은 비율로 바꾼다. 기준 배열은 읽기 전용 복사본이며 매 에피소드 복원한다. `mj_setConst`는 별도 임시 `MjData`로 실행하고 실제 data에는 `mj_forward`를 호출하여 시드 초기 자세·속도·목표/mocap·제어 입력을 보존한다.
- 바닥 마찰만 낮추면 발과의 최대값 혼합 때문에 의도한 접촉 변화가 생기지 않을 수 있어 바닥과 네 발을 함께 바꾼다.
- 위치 PD gain만 변경하지 않고 bias의 -kp/-kv와 실제 토크 제한도 함께 변경한다. torque 모드는 gain과 입력 변환에서 강도를 이중 적용하지 않는다.
- 행동·관측 지연을 실제 queue로 구현한다. 각각 2 control step 지연이며 행동은 영벡터, 관측은 완전히 생성된 초기 잡음 프레임으로 예열한다. 관측은 조회마다 새로 흔들지 않는다.
- 전체 관측에 임의 잡음을 넣지 않는다. 단위별 물리 센서에만 넣고 중력 방향을 정규화한다. 명령·목표·행동 이력은 측정 시각의 의미를 유지한다.
- 몸체 외력은 `xfrc_applied[base_id,:3]`의 세계 좌표계 힘으로 적용한다. `qfrc_applied`는 nv 벡터여서 몸체×6 인덱싱이 잘못되었다. 매 step 종료/예외/reset에서 제거한다.
- 병렬화 효과는 시작 비용과 steady 처리량을 실제 측정하며 고정 배수 가속으로 서술하지 않는다.

## 실행 증거

`evidence/section12_7/robust.json`에서 MuJoCo 3.3.7와 Torch 2.5.1 CPU 실행을 확인할 수 있다. 세 환경에서 실제 PPO를 각각 128 transition 학습하고 저장·재로드 후 추론했다. locomotion/goal은 DummyVecEnv, avoidance는 두 개의 SubprocVecEnv worker를 썼다.

| 과제 | 정책 파라미터 L1 변화 | 저장/재로드/추론 |
|---|---:|---|
| locomotion | 6.38946 | PASS |
| goal | 6.05589 | PASS |
| avoidance | 7.49007 | PASS |

첫 step에서 0.1 임펄스를 보낸 실제 trace는 적용 행동 `[0, 0, 0.1, 0, 0]`을 기록했다. 관측 행동 이력에 이 임펄스가 보이는 시점은 다섯 번째 step이다. 처음 두 관측은 reset 관측과 동일했다. 시드 31 → 32 → 31에서 첫/셋째 물성이 같았다. 확률 1로 설정한 외력은 실제 상태를 변화시켰고, 다음 step/초기화로 힘이 누적되지 않았다.

추가 회귀 19개는 비활성 wrapper의 기준 환경과 비트 단위 동등성, 각 링크 관성 비율, PD gain/bias/상한, torque 모드 강도 단일 적용, mocap 제외, reset 지연 제거, 과제별 관측 의미, PPO 파라미터 갱신을 확인한다. 세 과제에서 시드 4의 reset 높이 0.5m와 관절각 `[0.008861, -0.499773, 1.009525, ...]`가 기준 환경과 같고 속도·제어 입력·mocap·전체 관측도 정확히 보존됨을 확인했다. 물성 배열은 동시에 실제로 변경된다. 전체 suite는 **128 passed, 3 skipped, 14 warnings (15.90초)**이며 결과를 `evidence/section12_7/pytest_full.txt`에 저장했다. 무한 observation Box 관련 Gymnasium 경고 및 수치 불안정 감지 시험의 의도적 MuJoCo 경고는 기존 suite 출력이다.

독립 리뷰에서 초기 구현의 `mj_setConst(model, 실제data)`가 qpos를 qpos0로 덮어 초기 높이가 0.41m, 관절각이 0으로 바뀌는 결함을 재현했다. 세 과제 회귀를 먼저 실패시킨 후 임시 data 방식으로 수정했다. 수정 전 PASS 증거는 이 결함을 놓쳤으므로 `evidence/section12_7/before_reset_fix/`에 **무효/대체됨**으로 표시해 보존했다. 해당 디렉터리의 `reset_regression_red.txt`가 수정 전 실패 기록이다. 상위 디렉터리의 JSON·checkpoint·로그는 수정 후 다시 생성한 결과다.

## CPU 벤치마크

`evidence/section12_7/benchmark.json`: WSL2 Linux, Python 3.12.3, robustness 켬, zero action, warmup 20회 뒤 각 설정 vector step 100회. 초기 자세 수정 후 PPO 검증·벤치마크·전체 suite를 순차 실행했다. 공유 세션의 다른 시뮬레이터/검증 작업이 있으므로 독점 CPU 측정이나 재현되는 가속 배수를 보장하지 않는다.

| 환경 수 | Dummy 시작(s) | Subproc 시작(s) | Dummy transition/s | Subproc transition/s |
|---:|---:|---:|---:|---:|
| 1 | 0.022 | 3.105 | 274.6 | 159.7 |
| 2 | 0.086 | 3.384 | 222.8 | 332.2 |
| 4 | 0.117 | 4.029 | 208.6 | 596.0 |

환경 1개에서 subprocess는 느렸고, 시작 비용은 모든 경우에 더 컸다. 환경 수/모델/하드웨어에 따라 결론이 바뀌므로 학습 실행 전에 대상 과제로 다시 측정한다. 이 측정은 CPU MuJoCo이며 GPU 물리 가속 측정이 아니다.

## Gazebo와 검증 한계

실제 Gazebo의 공유 호환성 증거 `evidence/section12_6/gazebo/result.json`은 PASS이며 시뮬레이션 8.024~38.046초 동안 신선한 IMU·joint·scan·odom·pose/TF를 수집했다. 높이 0.24917~0.25020m, 최대 기울기 1.14298°, 정상 server 종료를 확인했다. 이는 기존 Gazebo 센서와 정지 자세의 실행 증거다. MuJoCo의 이 wrapper를 Gazebo에 적용했거나 Gazebo에서 무작위 물성 학습을 했다는 의미는 아니다. 12.8에서 정책과 ROS 명령 루프를 별도 검증한다.

짧은 PPO 갱신은 연결과 수치 안정성을 검사한다. 보행 숙련, 교란에 대한 보상 개선, 실기 전이 성능은 검증하지 않았다. 실제 하드웨어 구동은 수행하지 않았다. 지연 관측의 보상/종료 신호는 현재 transition에서 오므로 정책 학습은 부분 관측 문제를 다루며, 실기 센서 및 명령 타임스탬프와의 대응을 별도로 설계해야 한다.

## 공통 CLI 통합 검증

공통 `quadruped-train --task robust`로 실제 Subproc 2개 환경·256 transition을 추가 실행했다. 파라미터 L1 변화는 0.633326이며 번들 저장·검증·100 step 재생이 통과했다. 증거는 `ppo_runs/integrated/result.json`, `integrated_play.json`이다. 최종 전체 suite 결과는 12.8의 `green_final.log`에 **147 passed (34.23초)**로 기록했다. 이전 128개 결과는 당시 범위이며 최종 수와 혼동하지 않는다.