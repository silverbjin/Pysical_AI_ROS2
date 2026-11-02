# A 정착 원인 제한 조사와 보완 검토

2026-11-02 한국 시각. 사용자 요청에 따라 교재용 게이트를 조정하고 A만 제한 조사했다. **작은 배포 보완으로 실제 이동과 정착이 가능함을 확인했다.** 새 보행기·재학습·게인 수치 탐색은 하지 않았다. ROS2/Nav2 구현은 이번 범위에 넣지 않았다.

## 확인한 원인과 최소 보완

| 원인 | 확인 근거 | 보완 |
|---|---|---|
| 팔 목표가 live qpos view | 원본 대입문을 실제 MuJoCo 데이터에 적용하면 관측 변화가 명령 목표를 바꿈. 이전 시험에서 이미 입증 | 초기 팔 목표를 `.copy()`로 분리 |
| Python에서 계산한 팔 PD의 수치 불안정 | 동일 모델의 접촉 없는 국소 한 스텝 시험에서 손목 속도 교란의 증폭률3.905. integrator만 implicitfast로 바꿔도 동일 | 같은 Kp50/Kd4를 MuJoCo native affine PD로 표현하고 implicitfast 사용. 같은 초기 상태의 힘은 동일하고 증폭률0.831로 감소 |
| 정책 갱신 사이의 게인 선택 오류 | 원본 RL 활성 상태에서도10physics tick 중9tick이 stand50/5로 바뀜. 팔 보완 후 남은 body/leg 진동은약25Hz. 분기 실행 시험에서 실제50/5 선택 확인 | RL 활성 동안 원래 walking20/1.5 유지. 비활성 때 원래 stand50/5 유지. 두 대입식만 변경 |

마지막 항목은 게인을 새 값으로 조정한 것이 아니라 기존 모드의 선택을 일관되게 만든 것이다. 팔 보완은 같은 연속시간 PD 법칙을 유지하지만 이산 적분 방식은 달라진다. 따라서 원본 그대로의 PASS가 아니라 **명시된 Ch13 보완 profile의 결과**다. mass·inertia·접촉·physics2ms·정책 가중치·action scale은 바꾸지 않았다. 모델 원본 파일도 수정하지 않았다.

실제 actuator 힘 cap은 앞3팔축32Nm/뒤3축8Nm를 유지한다. 원래 torque motor의 ctrlrange를 native servo의 forcerange로 옮겨 힘에 적용한다. 새 arm ctrl은 rad 단위 위치 목표이므로 매 mj_step 직전에 원본의 팔 torque 입력을 덮어쓰는 경계가 필요하다. 이 단위 변경을 일반 torque topic으로 내보내서는 안 된다. 다리는 원래 controller가 소유한다.

MuJoCo3.13 문서는 actuator의 kv와 implicitfast/implicit 조합을 설명한다. Python에서 이미 계산한 motor torque에는 그 속도 미분이 노출되지 않는다는 판단은 실제 국소 시험으로 확인했다. [3.13 actuator 참조](https://mujoco.readthedocs.io/en/3.13.0/XMLreference.html#actuator-position), [적분 설명](https://mujoco.readthedocs.io/en/3.13.0/computation/index.html#numerical-integration), [힘 한계](https://mujoco.readthedocs.io/en/3.13.0/modeling.html#force-limits).

## 실제 재현 결과

전체 로봇 시험은 이번 제한 조사에서2회만 수행했다. 명령은 이전과 같은 5sim초0→5초전진vx0.2→5초0→4초회전wz0.2→6초0이다. 시험 전에 새 게이트JSON을 고정했고 두 실행에서 같은 SHA256 `a42263a8822eef0348d62ae9194a62033457e72929c44d2afdd00ac970dba3a2`를 사용했다.

| 실험 | 실제 결과 | 정착 판별 |
|---|---|---|
| 팔 native PD만 보완 `d03dbba9` | 25.002sim초/40.545wall초. 팔 큰 진동 제거. 마지막 팔 peak약0.150rad/s. body yaw RMS약0.301rad/s | yaw RMS만 FAIL. 이 실패는 보존 |
| 팔 native PD + 보행 모드 게인 유지 `0a384893` | 25.002sim초/40.837wall초, 실제 전진약0.957m·회전약0.570rad, exit0. 12,501physics step 모두 walking20/1.5 선택 | 기립 후·전진 후·회전 후3개 정착 창 모두 PASS |

최종 회전 후 정착 창의 실측값:

| 양 | 관측값 | 새 게이트 |
|---|---:|---:|
| 실제 창 길이 | 1.015wall초/0.638sim초·320고유 표본 | ≥1wall초/≥0.5sim초·≥25표본 |
| 평면 속도 RMS | 0.000454m/s | ≤0.05m/s |
| 창 안 xy변위 | 0.000289m(0.29mm) | ≤0.03m |
| yaw 속도 RMS | 0.000526rad/s | ≤0.20rad/s |
| 창 안 yaw변화 | 0.000337rad | ≤0.10rad |
| 팔 관절별 최대 RMS속도 | 0.000530rad/s | ≤0.20rad/s |
| 팔 관절 최대 변화 | 0.000338rad | ≤0.05rad |
| 팔 hold 목표 최대 오차 | 0.0201rad | ≤0.10rad |

속도는 engine sim초 단위이고 RMS는 sim시간 가중이다. 정착 창은 wall초로 잡되 실제 simulation도 전진해야 한다. 매2ms 물리 상태로 판별했으며 독립 계산으로 요약값을 확인했다. 최종 새 실행의 세 창 모두 이전의 더 엄격한 순간 속도 상한(3D선속도0.03/각속도0.05/팔0.1) 아래였다. **기준 완화만으로 통과시킨 결과가 아니다.** 과거 실행 결과는 재분류하지 않았다.

최종 실행의 contact 검사에서 발-환경 접촉 외에는 그리퍼 손가락 link7/link8 닫힘 접촉만 기록됐다. 팔 native PD만 보완한 중간 실행에는 짧은 FL_calf-환경 접촉도 있어 별도 보존했다. 최종 실행의 실제 actuator 힘은 원래 cap 이내였다. 모든 보행/장애물 장면의 충돌 안전을 입증한 것은 아니다.

[최종 요약](../evidence/section_13_5_reuse/0a384893-e928-4a23-919c-3d98b51f51be/summary.json), [독립 정착 계산](../evidence/section_13_5_reuse/0a384893-e928-4a23-919c-3d98b51f51be/independent_window_check.json), [정확한 두 줄 patch](../evidence/section_13_5_reuse/0a384893-e928-4a23-919c-3d98b51f51be/upstream_run_gain_selection.patch), [국소 수치 시험](../evidence/section_13_5_reuse/803b2f71-1073-44b7-b116-6355f66187fd/local_dynamics.json), [잔여 진동 분석](../evidence/section_13_5_reuse/803b2f71-1073-44b7-b116-6355f66187fd/residual_modes.json).

## 게이트를 교재 목적에 맞춘 방식

[게이트 개정 문서](SECTION_13_5_REUSE_EDUCATIONAL_GATES_KO.md)와 [고정 JSON](../dependencies/section_13_5_edu_stop_v2.json)에 반영했다. 매 순간 모든3D속도가 매우 작아야 하는 조건에서, 실제 목표 위치·방향·팔 hold가1초 유지되는지 확인하는 방식으로 바꿨다. raw peak는 보존하고 RMS·변위·자세 조건을 함께 검사한다. 반복은 고정본의 각 필수 사례1회를 유지한다.

비유한 상태·넘어짐·원래 힘 cap 초과·만료 관측·중복 소유자·시계 역행·고장 후 자동 재개 금지는 유지한다. Nav2 도착0.10m/0.10rad, 실제 terminal과 cancel ACK 구분, 실제 정착1wall초, 정상 종료·잔여 확인도 유지한다. 수정 후 최종 전체 matrix를 한 번 수행하고, 개발 중에는 영향 검사로 제한한다.

## 적용 판단과 후속 범위

A를 버리고 새 플랫폼을 만드는 대신, **현재 검증한 세 가지 최소 보완을 명시한 profile로 R2 연결을 진행하는 방향이 타당하다.** 원본 관측 구성·정책·다리 출력 소유권을 유지하고 Ch13은 안전 게이트와 ROS2 연결을 소유한다. 세 보완 helper는 [reproduce_upstream.py](../scripts/reuse_13_5/reproduce_upstream.py)에, 출처와 BSD 고지는 [재사용 명세](../scripts/reuse_13_5/REUSE_MANIFEST.md)에 기록했다.

이번에는 기립된 home 초기조건에서의 R1 이동/팔 hold를 확인했다. down→stand 전이, 최종 수납 envelope/IK·카메라/TF, 실제 DDS 소유권·만료/취소, stop latency, Nav2·비전 접근은 후속 검증이다. 회전 개방루프 추종은 명령0.8rad 적분 대비 약0.57rad로 차이가 있어 Nav2의 실제 위치 피드백으로 확인해야 한다. 원본 정책의0명령을 정책 비활성/torque0으로 대체하지 않았다.

팔 목표 보존·힘 법칙/포화·국소 수렴·물리 파라미터 보존·모드 선택의9개 작은 회귀 검사는 모두 통과했다. 최종 원본94개파일 해시와 게이트/helper해시를 대조했다. 최종 close 직후 Python thread 목록은 MainThread만 관측됐다. 후속 PID 조회에는 재현 worker 명령이 없었으며 WSL 재시작에 따른 PID 재사용을 구분했다. U6의 전체 ROS2 worker/RX join 시험은 아직 아니다.

단일 작업자 자체 검토를 수행했다. commit/push나 기존 Task8 재실행은 하지 않았다. 원래 checkout에서 이번 작업과 별개의 새 문서3개를 포함한35개 status 항목을 관측했고 손대지 않았다. 메시·가중치의 교재 재배포 여부는 별도 라이선스 검토 범위이며 이번 보완 코드의 수치 검증과 구분한다.
