# Ch07 §7.7 3개 작업 통합 — 작업① 오프라인 좌표·해제 경로 검증 보고서
_2026-11-17 | Issue #173 / #181 | Draft #204 | **STEP1_BLOCKED**_

> **인수 판정**: L0 정적 계산/테스트는 PASS, **물리적으로 무충돌인 해제 경로 후보는 미확보**, 따라서 STEP1_READY_FOR_L2 **아님**. 계획에 따라 ②의 물리 Goal/전체 E2E L2와 ③의 Owner WSL2 인수를 **실행하지 않음**. 물리 검증·로봇 motion·Gazebo·MoveIt 실행은 이 사이클에서 0건.

## 1. 먼저 확정한 계획과 코드 기준선

- 선행 [3개 작업 통합 실행계획](CH07_77_MINIMAL_THREE_WORKSTREAM_EXECUTION_PLAN_20261117_KO.md) (계획을 먼저 커밋한 SHA `27d0e7bbcf5bfaff96dd20e1baf7857fe43a1e27`).
- GitHub 기준 `main=9431fb535ce7a51416c19c4395fb2ba3fabdad40`. E2 통합 Draft [#204](https://github.com/silverbjin/Pysical_AI_ROS2/pull/204) `a69e1656537b406a1d51654e6710899785a37f8e`에서 진행. 이전 G04B [#202](https://github.com/silverbjin/Pysical_AI_ROS2/pull/202) HEAD `96d4f4d4b586687b1bc1243cc0e5a9d7901007ef`는 **main 기반이 아닌 진단 브랜치**; 전체 cherry-pick/병합 금지.
- E2 실제 카메라/G01/MoveIt plan_only [CI #43914056590](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43914056590) **SCOPED PASS 보존**, 다시 실행하지 않음.
- 재사용한 정적 소스: main `ci/ch07_77_g04a_graspable_fixture.py`; #202 `ci/ch07_77_g04b_physics_fixture.py`, `ci/ch07_181_fixed_world_base_anchor.py`, `ci/ch07_181_bin_yaw_single_factor.py`, `ci/ch07_181_exact_fk.py`, `ci/ch07_181_release_wrist_retract.py`; C17 실제 raw 요약·C18/C19 사후 진단.

## 2. 새 기능이 아니라 실제 인수 경계에 걸리는 다섯 개 물리 차이

| 물리 항목 | 이미 검증된 영상 G04A/E2 | 이전 파지 물리 G04B/C17 | 최소 통합에 미치는 영향 |
|---|---:|---:|---|
| 동적 원통 world X | 0.80m | 0.70m | 실제 이미지에서 도출한 target XYZ를 과거 grasp Goal에 그대로 넣으면 약 10cm 세계 좌표 불일치 |
| 원통 실제 높이 | **0.24m** | **0.08m** | G04A 영상은 **240mm 원통**; G04B 80mm 파지 형상으로 바꾸면 detector 픽셀 면적/중심·Depth 관측을 **재확인해야 함** |
| 원통 받침 상단 Z | 1.82m | 1.90m | 지지대·손목 선행 간섭 조건 다름 |
| 로봇 spawn/기준 | 원래 spawn Z=+0.05m | spawn Z=0 + Gazebo test-only world-base anchor | `base_link`↔world, 원통↔손끝 오프셋 일치 미검증 |
| Bin 회전 | yaw 0 | yaw 0.35rad | 원래 직육면체 Bin 충돌형상과 하강 clearance 조건 달라짐 |

**중요:** 두 원통을 동일한 '24mm rod'라고 기술하더라도 **지름 24mm만 같고 높이는 240mm와 80mm로 다르다**. 과거 `G04A` 영상 SCOPED PASS와 `G04B` 물리 조건 성공 일부를 합산해서 동일 세션 실제 RGB-D→그립 인수로 판정하는 것은 불가.

## 3. C17 원본 손목–낙하 원통 SAT 재계산 (정적·반증용)

- 실제 C17 [Run #43800612279](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43800612279), Artifact `14196048989`; native 물리 전체는 **wrist–rod 648건으로 FAIL**. 재사용한 pre-release arm `q=[0.509164, -0.331197, 1.049568, 1.569168, -0.346061]`rad, rod world `(0.503606, 0.238149, 1.914990)`m.
- 기존 #202의 원본 FK(원래 `Rz(q1) Ry(q2+q3) Rz(q4) Ry(qwrist)`, wrist `0.08×0.06×0.06m`)와 C18 보수적인 world vertical falling-rod AABB의 **Separating Axis Test**를 한정적으로 재계산했다.
- 원래 해제 자세의 보수적 wrist/drop SAT margin = **−0.029688m**. *이는 박스 겹침을 나타내는 정적 예측이지 native 실제 침투량을 잰 값은 아님.*
- C17 해제 자세 근방(기존 q2,q3,q4,wrist 변화 범위·bin 예측 XY≤0.06m·jaw drift≤0.245rad·tool drift≤0.375rad)을 고정하고 **총 1,570개** 후보를 정적 조회. 변한 자세에서 물체가 손가락과 rigid하게 동행한다는 실제 접촉 검증은 없으므로 **held offset을 일정 world vector로 가정한 screening에 불과**하다.
- 가장 큰 보수적 margin조차 **−0.01678273m**: 후보 변화 `Δq2=+0.08`, `Δq3=0`, `Δq4=+0.16`, `Δqwrist=−0.20`rad, 가상 예상 rod world `(0.600622,0.272424,1.854378)`m, bin XY 0.055366m. 이 후보도 **SAT 음수**이고 실제 grasp/collision-aware MoveIt/FCL·물리 동작을 확인한 적 없으므로 **Goal 후보로 선정/명령 금지**.
- 이 한정 샘플은 *다른 잡기 자세나 장치 구성이 원리적으로 불가능함을 증명하지 않는다*. 다만 **기존의 간단한 wrist/jaw 근방 목표 수치만 바꿔 E3를 안전하게 인수할 수 있다는 근거가 없다**는 점을 보여준다. C18/19의 0.8→0.25초 팔 후퇴 속도 시험은 native 충돌 620/535건으로 이미 실패했으므로 추가 속도 sweep은 금지.

## 4. 구현·CI·원본 증거

- 작성: `ci/ch07_77_step1_offline_geometry.py` (**순수 Python 읽기 전용**, source FK/SAT 및 fixture mismatch 확인), `ci/tests/test_ch07_77_step1_offline_geometry.py` (관련 테스트 **4개**), `.github/workflows/book-ch07-77-step1-offline.yml` (3분 L0, ROS/Gazebo 설치 없음).
- [GitHub Actions #43978311609](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43978311609) **SUCCESS**, Job `read-only-c17-source-bound-gate` 성공, 4/4 집중 테스트 통과. Artifact [#14282896001](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43978311609/artifacts/14282896001) `offline.json`; 원본 ZIP 로컬 다운로드 SHA256 `cf0f0a6a3590545a39bc6f07d41c60ec1b376aba9b925cd55299be9c43f81121`.
- `offline.json` 실제 필드: `status=STEP1_BLOCKED`; `bounded_collision_free_candidate_found=false`; `physics_goal_authorized=false`; `step2_e2e_l2=NOT_RUN`; `owner_wsl2=NOT_READY`. **CI SUCCESS는 실패 상태를 올바로 검출했다는 증거이지 물리적 무충돌 PASS가 아니다.**
- 범위: ROS motor Goals 0건, Gazebo 실행 0건, 기존 E2/G04A 실제 성공 재시험 0건. physical #202 기존 증거는 변경되지 않았고, raw verdict/허용차도 변경하지 않았다.

## 5. 작업 ① 판정 및 작업 ②·③ 의존 규칙

**`STEP1_BLOCKED`**. 다음 단계인 실제 E2E 구동으로 넘어가기 위해 꼭 필요한 근거가 아직 3가지다:

1. **단일 실제 물리 월드:** 과거 G04B 80mm × 24mm rod와 원래 RGB-D 카메라/로봇을 동일 SDF/URDF/world/base에 놓고, **그 월드에서 실제 optical RGB·Depth·G01 source target**의 live 유효성을 검증. E2의 240mm 원통 예전 감지 좌표 재생 금지.
2. **보정:** 그 실제 센서 기반 `base_link` surface XYZ→**실제** rod center→finger jaw/TCP/world 변환의 수치 검증. 고정값 `-0.15m/-0.09m` 초기 계획 오프셋은 physical calibration이 아님.
3. **명확한 새 release 안전 후보:** 기존 손목–rod drop overlap을 실제로 해결하는 *하나의* 형상/파지 자세/순서 수정 가설, 해당 후보의 **MoveIt/FCL plan_only collision-free** 및 원래 bin·관절·jaw 물리 제약을 보여주는 오프라인 결과. C17 근방의 단순한 q4/wrist 튜닝이나 속도만 바꿔서는 현재 근거가 없음.

**따라서 계획의 fail-closed 조건대로 작업② 실제 물리 실행 및 작업③ Owner WSL2 최종 인수를 이 턴에서 시작하지 않는다.** 이 판단을 '작업 완료'나 전체 PASS로 표현하지 않는다. 미준비 단계에 실행 코드를 붙이는 것은 지금 사용자가 제한한 과도한 개발 확장의 재발이다.

정확한 다음 상태:
```text
THREE_WORKSTREAM_PLAN=COMMITTED
STEP1_SOURCE_BOUND_L0=PASS
STEP1_PHYSICAL_GEOMETRY=BLOCKED
STEP2_SAME_SESSION_PHYSICAL_E2E=NOT_RUN
STEP3_OWNER_WSL2=NOT_READY
E2_SENSOR_TO_MOVEIT_PLAN_ONLY=SCOPED_PASS [prior preserved]
G04B_PHYSICAL_CLEAN=BLOCKED
CH07_77_E2E=BLOCKED
G05=NOT_RUN
Ch10=HOLD
```

**후속 한계:** 신뢰할 수 있는 실제 source/scene/collision-free 후보가 없다면 새로운 실물 구동 테스트를 추가하지 않는다. 사용자와 함께 선택한 출판 범위 안에서 물리 집기 완료까지 필요하다고 합의한 경우에만, 위 3가지 근거를 만족하는 *한 가지* 새로운 기하학적 해결안을 별도 후보로 검토한다.
