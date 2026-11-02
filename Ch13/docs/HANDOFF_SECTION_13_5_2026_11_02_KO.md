# 13.5절 작업 인계 — 2026-11-02

> **미완료 인계다.** Task8의 Gazebo G1은 통과하지만 C1은 두 발 전환 후 실패한다. 전체 G2·고정본 연속 성공·Nav2 Tasks9–14·최종 회귀·절 단위 commit/push는 남아 있다. 최신 실패를 제외하고 성공만 세지 않는다.

## 1. 새 창의 시작 지시

다음 순서로 상태를 복원한다. 과거 전체 대화/로그를 다시 읽거나 기존 EGL·수신·수학 커널을 처음부터 구현하지 않는다.

1. 실제 HEAD·브랜치·작업트리·적용 AGENTS.md를 확인하고 사용자 변경을 보존한다.
2. 이 문서와 `.superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/CURRENT_TASK_STATE.json`을 읽는다. checkpoint의 오래된 `implemented`, `preflight`, `do_not_repeat` 필드보다 이 문서의 최신 결과가 우선한다.
3. `Ch13/docs/SECTION_13_5_LOAD_TRANSFER_REDESIGN_KO.md` 상단 최신 세 항목과 아래 지정한 최소 evidence를 읽는다.
4. **즉시 전체 로봇 엔진을 재시험하지 않는다.** 현재는 명령 토크와 물리 전달/모델의 관계를 판별할 단계다. 다음 최소 물리 시험은 아직 작성·실행하지 않았다.

작업은 서브에이전트 없이 네이티브 단일 작업자로 진행한다. 환경에 `/root/final_review`가 보여도 이 작업에 사용하지 않았다. 사용자가 모델별 유연한 운영을 요청했지만 주 작업자의 모델 전환 도구는 없었으므로 모델을 전환했다고 쓰지 않는다.

## 2. 저장소·환경·현재 프로세스

- 저장소: `C:/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2`
- 브랜치: `feat/ch13-section-13-5`
- HEAD: `4e87f6f6031d0ac5e73b2575bcee261e92a0e59e`
- 이 창에서 **새 commit/push 없음**. 기존의 대량 수정·미추적 파일을 보존했다. `git reset/clean`, 전체 파일 일괄 stage, stale lock 삭제를 하지 않는다.
- 사용자 파일 `Ch13/docs/SECTION_13_4_DEBUGGING_LESSONS_KO.md`: 40,723B, SHA256 `659d8acf7fc6ef266275520c71f6383cc1038e823625e44a093d6ac797a21bc4`. 수정하거나 stage하지 않는다.
- 마지막 확인에서 Ch01–12 및 저장소 `sources`의 추적 변경은 없었다. 프로젝트 상위 `sources/`도 읽기 전용이다.
- WSL: Ubuntu-24.04, 일반 사용자 `jinho`, ROS2 Jazzy. Windows 쪽 쉘은 PowerShell이다.
- 네이티브 작업 루트: `/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b`
- 기존 underlay `/home/jinho/ch13_mujoco_ws`, Python 환경 `/home/jinho/ch13_vision_13_4_venv`는 원본 수정 금지.
- Windows Python: `C:/Users/Jinho/AppData/Local/Programs/Python/Python311/python.exe`
- **활성 엔진·서비스 임시 변경·수치 자식·실행 중 검사 없음.** 마지막 실제 root는 복원/foreground 종료/잔여[] 확인 후 끝났다. idle keepalive도 없다.
- WSL boot ID가 자동으로 바뀐 구간이 있었다. 이 창에서 WSL 종료/재시작을 지시하지 않았다. 시작 시 `/etc/wsl.conf:3 boot.appendWindowsPath` 경고가 있으나 외부 설정을 수정하지 않았다.

아래 약어는 모두 저장소 상대 경로다.

| 약어 | 경로 |
|---|---|
| T | `.superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO` |
| B | `Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b` |
| N | `Ch13/ros2_ws/src/integrated_robot_navigation` |
| NP | `N/integrated_robot_navigation` |
| S | `Ch13/ros2_ws/src/integrated_robot_navigation_sensors` |

## 3. 변하지 않는 계약과 승인

Ch13 내부 설계·worker·callback·cache·제어 수명 개선은 승인 범위에서 진행한다. 매 세부 선택마다 다시 승인을 요청하지 않는다. 시스템 권한/드라이버/범위 밖 변경이 실제로 필요하면 구체적 결과와 필요한 결정을 묶어 질문한다.

- 외부 checkout/underlay, Ch01–12, 동기화된 `sources/` 수정 금지. 필요한 복사는 라이선스·출처·커밋 기록.
- 물리2ms, Controller Manager100Hz, 고수준50Hz, 기존 게인 및 hip20Nm/thigh·calf30Nm 유지. 실제 calf kp는750일 수 있다. 80으로 가정하지 않는다.
- unload 벡터2mm/s·총10mm·6ROS초, 실제 Fn<2N100ms 유지.
- swing20mm/s·높이20mm·발 변위80mm, G1 10wall초 및1wall초 실측 정착 유지.
- 수치 커널 전체10ms·최대32회, 원래 완전 수신40ms, 관측 ROS/wall200ms 유지. 새 same-cycle 거래에는 **추가 전체10ms 상한**이 있다.
- §13.4의320×240/camera15Hz/inference10Hz 기본·15Hz 선택/촬영 및 수신 age300ms/과거TF100ms/팔5Hz는 변경하지 않는다.
- 최신 TF 대체·header now 변경·오래된 목표 유지·실패 후 자동 재시도/재활성화 금지. 관절·TF·명령 단일 소유권 유지.
- MuJoCo 다리 참조20ms 보간은 사용자가 거절했다. native 유지.
- 실제 엔진은 순차 실행하고 정상 종료·소유 프로세스 회수·잔여·서비스 복원을 확인한 뒤 다음 엔진을 시작한다. SIGTERM/KILL이나 잔여 없음으로 정상 종료 실패를 숨기지 않는다.
- 현재 actual harness는 승인된 두 timesync 서비스만 임시 중지/복원하고 tick은 **읽기 전용**이다. 현재 날짜/시각·드라이버·Windows 관리자·ptrace·priority 설정 변경 금지.
- 실제 root 활성 중에는 빌드·pytest·원본 분석·압축·추가 CPU 수집을 하지 않고 작은 상태 파일/로그 tail만 확인한다.
- 새 실행은 UUID·소스/설치 SHA·실제 명령·결과를 보존한다. 대용량 원본을 Windows evidence로 무조건 복사하지 않는다. 원본 삭제는 검증된 보존/압축·경로 검사를 거쳐야 한다.

## 4. G1/G2/C1의 구분

- G1: 센서·팔 수납·기립·실제 교정 lift/return·정착 등 기존 독립 인수 게이트.
- G2: 실제 전진/좌·우/정지와 소유권·안전·종료까지 포함한 전체 저속 crawl 인수.
- C1: G1 통과 모델로 네 발의 실제 하중 해제·들기·복귀를 먼저 확인하는 **부품 진단**. 전체 G2가 아니다. 일부 G2 검사는 사전에 미실행으로 명시된다.

현재 네 발 C1 완료도 아직 없다. 과거 G1 성공을 새 G2 성공으로 세거나, C1의 사전 미실행 항목을 제거해 G2 PASS로 만들면 안 된다.

## 5. 이미 구현·검증한 내용 — 재구현하지 말 것

1. 기존 complete native kernel: 접촉/질량 계산→12좌표 QP→정확한 IK·28표본 기하를 한 번의 호출로 연결. QPMAD1.5.1의 고정 커밋은 `11602ec9f87a62a97ba8318ebd81da6646f3c631`, vendor 원본 불변. 전체10ms/32회 유지.
2. 고정 좌표 정확 치환, L1/box 등가 presolve, Hessian metric 행 정규화. 기존72/130 실패 입력의 반복 예산 문제를 해결했고 원래 전체 행/box 검사를 유지했다.
3. 원래 허용 box roundoff만 정확 경계로 복원한 뒤 전체132개 행과 힘/토크/기하를 재검사. 이전 job57의 -5e-22m 선택 발 deltaZ 거부를 부모에서 완화하지 않았다.
4. `numeric_receipts.py`: 단일 read-only RX thread/최대1완전 응답 slot. JSON 완료 시 실제 수신 시각을 고정, partial/덮어쓰기 금지. 종료는 RX join→기존 STOP/ACK→핸들 해제→회수. 실제 정상 종료 증거 있음.
5. `inverse_remainder.hpp`: 자체 FK Hessian 상계와 국소 역함수 contraction으로 IK 비선형 나머지를 계산하고 servo QP 영역을 안쪽으로 제한. 원래 정확한20/30Nm+1e-6 검사는 유지. 실제121의 선형-30/정확-30.0000179Nm 실패는 단독 회귀로 해결. C++17검사 및 실제 입력 포함22검사 통과.
6. **same_cycle**: 명시적 Gazebo G2에만 현재 관측 한 묶음을 기존 수치 자식에 한 번 제출하고 같은 모델 주기에서 검사·반영. 전체 거래10ms/원래 커널10ms·40ms 수신·200ms 관측 유지. 사전 다음 작업 제출·자동 재시도 없음. 기본/G1/MuJoCo는 유지. `strict`와 `mature_horizon`도 비교용으로 남음.
7. **maintenance**: same-cycle SHIFT unload 중 몸체 unsettled이면 선택 발 XYZ를 정확히 고정하고 현재 측정 네 발 힘을 목표로 지지 다리만 보정. 정착 기준을 낮추지 않았다. 정상 전체 미래 기하 증명 없이는 release dwell/SWING 불가. **실제 최신 시험에서 이 수정만으로 실패를 해결하지 못했다.**

주요 수정 소스는 NP의 `gait.py`, `load_process.py`, `numeric_receipts.py`, `crawl_controller.py`, S의 `src/xyz_optimizer.cpp`, `include/.../inverse_remainder.hpp`다. maintenance는 native ABI를 바꾸지 않고 선택 발 allowed_z/future 목표를 현재 한 점으로 좁힌다.

## 6. 이번 창의 실제 실행 결과

각 root는 첫 실패 후 종료했다. 모든 아래 실행에서 root 서비스 복원·foreground 종료·잔여[]를 확인했다. 수치 자식의 RX join/빈slot/STOP ACK/세 핸들 해제/회수와 엔진/runtime 정상 종료도 통과했다. **과제 성공과 종료 성공은 별개다.**

| root / 호스트 witness | G1 | C1 / 최초 실패 |
|---|---|---|
| `ae53a6b0-bead-45ec-8f6e-db91fabbdf17` / `4e6e05ec…` | `1e1a438c…` PASS | `dbdfa89a…` FL·RR 완료 후 성공 job325를 새 관측에 적용할 때 current servo 초과. 입력29.9979→현재30.0168Nm,10ms 관절 변화25.2647µrad. |
| `235a5ec8-5924-40e3-b8b4-00b9ae5ca629` / `de8f1b10…` | `7264d7d5…` PASS | `ab85a9a6…` same-cycle에서도 FL·RR 완료 후 job264 infeasible. 거래1.1533ms,263완료/폐기0/실패1. |
| **`5597f39f-3aab-4551-80f4-2fe6e4ea96f3`** / `6b503434…` | **`4a209b11-b39e-4fed-a547-863466dacf24` PASS** | **`d50469aa-b0a0-402b-b8e5-f59f21ad31a0`** maintenance 추가 후에도 FL·RR 완료, FR 준비의 **job267 infeasible**. 거래2.318899ms,266완료/폐기0/실패1. |

최신 실패: ROS53.136초, FR unload 시작52.310초, 현재 FL calf P=-30.3005609Nm/관절 속도0.0208904rad/s. 마지막 요청은 `maintenance:false`인 정상 unload 요청이다. 새 경로의 시간 초과나 원래 IK 나머지 실패가 아니다.

## 7. 현재 가장 중요한 미해결 원인 판별

### 확정된 근거

- 실패264의 독립 HiGHS/Farkas 증명(`B/infeasible-264-e19a7f50-ac4a-480b-95db-1f0833782d85/result.json`): FL calf servo 하한·step L1 두 행·Z 상한 네 행이 충돌. 비음수 y에서 `max|Aᵀy|=5.55e-17`, `bᵀy=-1`. 반복 한도 증가로 해결할 문제가 아니다. 이것은 **해당 현재 관측의 국소 문제**이지 몸체 재배치까지 포함한 전역 불가능 증명이 아니다.
- `B/settle-feedback-window-50ec6795-39e1-4e8c-8ffa-735f2ace962b.json`: unload 중40~60ms씩 정착 기준 밖의 구간이 반복된다. 이전 코드는 그동안 지지 피드백도 끊었다. maintenance로 이를 분리했지만 최신267 실패는 남았다.
- `B/maintenance-264-075b380d-95c2-4ee0-932f-861f4ac7b8f2.json`: 원래 실패 직전 기록에서 선택 발 고정/현재 힘 목표의 세 후보와 다음 정상 후보는 원래 제약을 통과했다. **반사실 후보 검사이며 실제 폐루프 성공이 아니다.**

### 최신 물리 일치성 진단 — 다음 작업의 출발점

`B/plant-consistency-0d186449-0c02-4413-a237-52ec19b78465.json` 및 앞선 `plant-consistency-62719d20…`를 읽는다. 방법은 `T/diagnose-plant-consistency.py`, 실행 로그는 `B/task8-plant-consistency-stages.log`다.

- 질량15.2101kg, 실제 접촉력 합 z149.0782N, 현재 CoM 기준 접촉 토크 약[-0.0446,0.0510,-0.00064]Nm. 접촉 전체가 무작위로 잘못 연결됐다는 근거는 없다.
- 실패 부근 FL calf의 `force_command`=-30Nm, 부모 요청 P=-30.30056Nm, native 적용 참조로 계산한 P≈-30.50Nm.
- 같은 부근 모델 `gravity−JᵀF`≈-7.6115Nm, native `projected_transmitted_effort`≈-7.6122Nm.
- **10–20ROS초 정지 구간500표본**: 평균 |force_command|=20.02994Nm, 평균 |projected_transmitted_effort|=5.20617Nm, 최대 |qd|=0.0001421rad/s. force_command=0 표본은0개.
- 전달 렌치의 축 성분을 실제 actuator effort라고 단정하지 않는다. 진단 JSON도 이 한계를 명시한다. 단순히4배 계수를 곱하거나 Kp를 바꾸면 안 된다.

공식 소스에서 확인한 사실:

- 설치: `ros-jazzy-gz-ros2-control=1.2.20`, `ros-jazzy-hardware-interface=4.48.1`.
- [gz_ros2_control 1.2.20](https://github.com/ros-controls/gz_ros2_control/blob/1.2.20/gz_ros2_control/src/gz_ros2_control_plugin.cpp): PreUpdate에서 manager.write를 매 physics step 호출하고, read/update는 control period로 수행한다.
- [Gazebo sim8 Physics](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/physics/Physics.cc): JointForceCmd를 엔진 SetForce로 전달하고 이후 명령 성분을0으로 비운다.
- [ros2_control 4.48.1 HardwareComponent](https://github.com/ros-controls/ros2_control/blob/4.48.1/hardware_interface/src/hardware_component.cpp), [trigger_write](https://github.com/ros-controls/ros2_control/blob/4.48.1/hardware_interface/src/hardware_component_interface.cpp): 동기 hardware write 경로 확인. 현재 URDF rw_rate/is_async는 명시되지 않았다.
- Ch13 `PositionPDSystem::write`는 현재 q를 다시 읽어 `clamp(kp*(applied−q), ±effort)`를 쓴다. 별도 explicit KD는 없고 URDF native damper 사용. FL calf damper10.95445이며 위 정지 속도에서 큰 토크 차이를 설명하지 못한다.

**아직 검증하지 않은 가설**: 명령 적용 단계/샘플 위상/렌치 의미/물리 actuator 경로의 불일치. 상위 force controller에 임의 토크 여유를 더하기 전에 판별한다. 매 step 명령이 누락된다고 아직 확정하지 않았고, llvmpipe·시계·모델 성능 하나를 원인으로 단정하지 않는다.

### 다음 최소 판별 실험(아직 코드·실행 없음)

공식 `gz::sim::TestFixture`가 설치돼 있음을 확인했다. 헤더:
`/opt/ros/jazzy/opt/gz_sim_vendor/include/gz/sim8/gz/sim/TestFixture.hh`.
`OnConfigure/OnPreUpdate/OnPostUpdate/Finalize/Server()` 사용 가능.

가능한 순서:

1. 중력0·알려진 관성·단일 자유 회전 관절·2ms의 작은 Gazebo 세계를 별도 Ch13 진단에 작성한다.
2. 매 PreUpdate에서 알려진 힘을 쓴 경우와 제어 주기 때만 쓴 경우를 **사전에 정의한 두 판별 조건**으로 비교하고, Δqd가 `τ·dt/I`와 맞는지 확인한다. 원래 물리/제어기를 바꾸는 성공 시험이 아니라 적용 의미 판별이다.
3. 전달 렌치 축 성분과 명령/관절 가속도의 관계도 함께 확인한다. 짧은 고정 step 실행과 정상 서버 종료·잔여 확인, 작은 요약만 보존한다.
4. 필요하면 기존 Ch13 plugin의 bounded ring에 매 physics step 실제 명령 적용 경계를 계측한다. ROS100Hz와 물리500Hz의 경계·native 시각을 구분한다. 데이터가 없다고 callback 부재라고 단정하지 않는다.
5. 원인이 판별된 뒤 실패 회귀→최소 수정→영향 검사→고정본 실제 G1/C1으로 간다. 외부 설치 소스를 수정하지 않는다.

이 계획은 아직 판별 후보다. 공식 API·현재 소스를 확인해 더 작은 실험으로 충분하면 그것을 택한다. 같은 전체 엔진 시험이나 파라미터 조합을 무작정 반복하지 않는다.

## 8. 테스트·fixture·실패 보존

현재 maintenance 소스의 N 빌드9.37초/8패키지 감사 PASS. 이후 런타임 수정은 없었다.

- `task8-maintenance-green-v2.log`: 새 유지/거래10검사 PASS15.50초.
- `task8-maintenance-related.log`: 영향14파일108검사 PASS101.82초.
- `task8-maintenance-release-proof.log`: 유지 기하 증명으로 SWING 금지1검사 PASS10.97초.
- 앞선 inverse-remainder CPP17/2ms, complete22/16.69초, 관련38/36.76초 PASS. 이후 native 수학은 바뀌지 않았다.
- same-cycle79/69.27초 + 부모 파일12/10초 PASS. 단, 최초 묶음의 기존 Python 비교 계산10ms 실패는 보존하며 원인 해결이라고 주장하지 않는다.
- 과거 default height/model_poll의 간헐10ms 실패도 미해결 기록이다. 분리 시험 PASS와 구분한다. 최종 전체 시험에서 해당 사례를 제외하면 안 된다.
- 초기 새 유지 시험의 준비 오류(`_offset_start` 누락), 가짜 fixture 시각과 실제 clock 혼용 오류도 로그에 보존했고 시험 준비만 바로잡았다.

최소 fixture(모두 N/test/fixtures):

| 파일 | SHA256 / 의미 |
|---|---|
| `native_1a62_nonlinear_servo.json` | `ba8708696b5d5488c495f87aadfe0e2ce2e1544ec6b268381854a133e8ac70e0`, 실제 실패121 |
| `native_dbdf_current_servo.json` | `de23c7c60ea12f5886ca987b7e34d300ccc431ad58db38aef5ecf2f005b4f1e2`, 성공325/부모 거부 |
| `native_ab85_infeasible.json` | `19cc4abd30210422c4aaba23c8f1d6fd2e97cdde7658f9ae35b2400d5f658b87`, 실제 실패264 |
| `native_d504_infeasible.json` | `799e3b0b088b1b7eaade804934fb589549d382c6110f122f21838301fb79d3bb`, 최신 실제 실패267 |
| `native_ab85_maintenance_window.json` | `46c7eb22cd90e5dccd68143b1fae69eeb38fa373c33a50e40dbbf34d0e408ec5`,68,717B 반사실 회귀 |

실패 입력 추출은 `T/export-failed-xyz-fixture.py`의 ID/응답 ok=false 가드를 사용한다. 성공 수치/부모 거부는 별도 명세로 추출해야 한다. 이전 성공 입력을 나중 실패 입력이라고 쓰지 않는다.

## 9. 실행 도구와 evidence 위치

모든 명령은 저장소 루트에서 실행한다. LABEL은 기존 파일을 덮어쓰지 않는 새 값으로 정한다.

```powershell
wsl.exe -d Ubuntu-24.04 -u jinho -- bash .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/build-native-n.sh LABEL
wsl.exe -d Ubuntu-24.04 -u jinho -- bash .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/audit-native.sh LABEL
wsl.exe -d Ubuntu-24.04 -u jinho -- env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 bash .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/check-native.sh LABEL TEST_PATH
```

- `T/build-load-redesign.sh`: I/S/N 빌드+감사. S를 바꿨을 때 사용. **S/REUSE_MANIFEST.md까지 고친 뒤 빌드**한다. 빌드 후 S 문서를 바꾸면 설치 감사가 실패한다.
- 이미 빌드한 C++ 테스트는 네이티브 build의 binary를 직접 실행한다. 불필요한 CMake 재설정을 반복하지 않는다.
- `T/check-load-redesign.sh`: 최종 폭넓은 load 회귀 목록. 새 numeric_receipts/same_cycle/stance_maintenance도 포함했다. 최종 동결 전 반복 전체 실행하지 않는다.
- 실제 full G1→C1 wrapper는 `T/host-performance-witness.py --run`. Windows Python으로 실행하며 기본 경량2초 PDH를 사용한다. `--process-cpu`는 기본 제외한다.
- wrapper가 prelease8감사→승인된 두 서비스 lease→원본 시계 검사→실행→정리/복원을 소유한다. 명령은 service-only/tick read-only/single-pair/Gazebo/C1 진단이다. **다음 최소 물리 판별을 마치기 전 그대로 재실행하지 않는다.**
- 원본 대용량 latest native_controls는 네이티브 루트의 `evidence/native-contact-component-gazebo-d50469aa-b0a0-402b-b8e5-f59f21ad31a0/native_controls.json`(약83MB). 원본 CDR/JSONL도 같은 폴더에 있다. 진단은 이를 읽고 작은 요약만 B에 저장했다.
- `B/EXECUTION_LEDGER.md`는 누적 기록이다. 최신 root267와 물리 진단은 이 인계 문서와 함께 읽는다.

## 10. 완료까지 남은 일

1. 위 물리/명령 일치성 원인 판별과 필요한 최소 수정, 실제 C1 네 발 완료.
2. 실제 전체 G2, MuJoCo/Gazebo 고정 소스3회 연속 및 기존 역순 검증. 실패를 빼고 성공만 골라 세지 않는다.
3. 승인된 저속 crawl을 이동기로 사용해 Nav2 Tasks9–14. 먼저 `SECTION_13_5_RESEARCH_DECISIONS_KO.md`와 기존 task brief의 성공 사례를 재사용하고 필요한 최신 공식 자료만 조사한다.
4. 최종 소스 동결 후 전체 패키지·설치 일치 감사·기존13.3/13.4 required matrix와13.5 회귀. 이후 runtime 수정 시 영향받는 실제 시험 재실행.
5. 한글 가이드·REUSE·리뷰/변경 보고서·evidence 보존 보고를 갱신하고 절 단위 commit/non-force push, 최종 원격 SHA 일치 검증. main 병합/PR 생성/force push 금지. 동명 브랜치가 원격에서 분기됐으면 덮어쓰지 말고 사용자 승인 정책에 따라 새 이름을 사용한다.

PPO 적재 보행·MoveIt·물리 파지·새13.6 확장은 이 단계에 추가하지 않는다. 단위 검사·계측 완료나 정상 종료만으로13.5 완성을 선언하지 않는다.
