# 13.6 정밀 매니퓰레이션 패키지 개발 인계

> 새 작업 창의 후속 작업자는 이 문서를 먼저 읽는다. 단일 작업자로 진행한다. 기존 공개 Go2+Piper 패키지를 기반으로13.6 실습 패키지를 개발한다. 이번 작업에서 완료한 것은 인계 문서 작성이며13.6 구현·설치·엔진 실행은 하지 않았다.

작성일: 2026-11-03, 한국 시각.

## 1. 사용자 요청과 범위

사용자는13.5 공개 플랫폼 패키지를 기준으로13.6 내용을 실습할 패키지를 **새 작업 창에서 개발**하기 위해 인계를 요청했다. 이 창은 인계 문서만 작성한다. 새 창/브랜치/패키지는 아직 생성하지 않았다.

현재 확인된 장 간 연결은 “Nav2 접근·실제 정착 → Piper 팔의 정밀 조작”이다.13.5 원고의 다음 절 예고에는 MoveIt2와 물체 picking이 있다. 다만 **13.6 전체 원고는 이 대화에 제공되지 않았고 로컬 Ch13 문서에서도 발견하지 못했다.** 아래 개발 단계는 그 연결을 위한 제안이다. 후속 작업자는 연결된 프로젝트 자료에서13.6 원고를 먼저 찾고, 없으면 사용자에게 본문/필수 과제를 요청하면서 모델·인터페이스 조사를 진행한다. 제목·소절·시각 피드백·파지/놓기 범위를 임의로 승인된 명세로 확정하지 않는다.

교육용 실습의 우선 목표는 현재 모델/정책 재사용, 실제 팔 명령·관측과 MoveIt 실행 연결, 그리고 원고가 요구하는 조작 과제다. 새 보행기·재학습·전신 최적화·실기/드라이버·Gazebo 동등 구현은 기본 개발 범위에 넣지 않는다. 단순 관절 도달과 물리 파지 성공은 구분한다.

## 2. 실제 저장소·브랜치·게시 상태

**작업 저장소:**

```text
C:/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse
```

문서 작성 직전 확인:

- 브랜치: `feat/ch13-section-13-5-reuse-r2-20261102`.
- 기준 HEAD: `58fd73ea7277657f70e702220ba425b690bdc7c0`.
- 기준 commit: `docs(ch13): record lab guide verification and publication report`.
- 직전 턴에서 실제 원격 SHA 일치를 확인했다. 후속 실행 때 다시 조회한다.
- 이번 문서 작성 전 작업트리는 clean이었다. 이 문서 게시 후 HEAD는 문서 commit만큼 달라진다. 실행 기준은 아래 v3 hash 목록이다.
- `work/Pysical_AI_ROS2`는 과거 Task8의 다른 작업트리다. 새13.6 개발 위치로 혼동하지 않는다. 이전 dirty/evidence 정리 상태를 임의 복구·삭제하지 않는다.
- `work/Pysical_AI_ROS2_guide_validation_20261103`는 다운로드 검증용 별도 clone이며 개발 기준 저장소가 아니다.
- 이번 인계 작성에서 WSL/Windows 전체 프로세스를 새로 조회하지 않았다. 직전 실행의 정상 회수 기록이 현재 무실행 상태를 영구 보증하지 않는다.

원격: `https://github.com/silverbjin/Pysical_AI_ROS2.git`. 사용자는 이 저장소에 Ch13 소스·보고서·실험 증거(로컬 경로 포함, 모델/가중치 제외)를 게시하도록 승인했다. non-force push만 한다. main 병합/PR은 지시가 없다. 새13.6 브랜치 게시가 승인 검토에서 다른 대상으로 판단되면 구체적 거절 이유와 필요한 범위만 확인한다.

## 3. 먼저 읽을 자료

1. [따라 하는13.5 가이드](LAB_13_5_REUSE_GUIDE_KO.md): 소스·94자산 다운로드, venv, build, 터미널 환경, 실행·결과 판독.
2. [공개 플랫폼 설계](SECTION_13_5_REUSE_DESIGN_KO.md), [출처 명세](REUSE_MANIFEST.md).
3. [R5 최종 인수](SECTION_13_5_REUSE_R5_REPORT_KO.md), [게시 확인](SECTION_13_5_REUSE_R5_PUBLICATION_KO.md).
4. [가이드 개정 보고서](SECTION_13_5_REUSE_GUIDE_REVISION_REPORT_KO.md): 최근 대표 재현의 성공·실패·한계.
5. [정착 제한 조사](SECTION_13_5_REUSE_SETTLING_REVIEW_KO.md), [R2 가이드](LAB_13_5_REUSE_R2_GUIDE_KO.md): 팔 독립성 확인의 실제 범위.
6. [v3 실행 파일 목록](../dependencies/section_13_5_reuse_acceptance_v3.json), [자산 lock](../dependencies/section_13_5_reuse.lock.json), [교육용 정착 기준](../dependencies/section_13_5_edu_stop_v2.json).

이전 Task8 인계는 역사 기록이다. 그것을 새 작업의 자동 재실행 계획으로 삼지 않는다. 이전13.3/13.4 로봇의 팔 관절명/카메라/MoveIt 설정을 새 Piper와 같다고 간주하지 않는다.

## 4. 현재 검증된 기반과 한계

- Ubuntu24.04/WSL2, ROS2 Jazzy, Nav2 1.3.13, Python3.12.3, MuJoCo3.13.0, CPU Torch2.9.0+cpu·ONNX Runtime1.31.1 조합.
- IIT-DLSLab upstream `d010212c3f5c9e6e5542ada61cfdacc19b00f775`, 외부94파일 hash 고정. 모델과 가중치는 저장소에 재배포하지 않는다.
- actor 다리12출력, 원본2ms 물리/50simHz 정책. corrected A의 팔 참조 고정/native PD/보행 gain 일치 보완과 프로세스 내부 단조시계·CPU 추론 제한을 사용한다. 새 학습은 없다.
- v3 실행114파일 동결. R5 free/obstacle/blocked/cancel/vision/raw_loss 각1회 PASS. 그 기준이나 과거 FAIL을 새13.6 결과로 덮지 않는다.
- 가이드 검증에서는 free PASS, vision 첫 실행 VISION_EXPIRED FAIL, 동일 기준의 vision_retry PASS를 모두 보존했다. 최근 위치 오차는 각각0.044305m/0.036725m다. 원인 미확정의 관측 지연을 “해결됐다”고 쓰지 않는다.
- 카메라는 실제320×240 렌더·원본 depth·과거 TF를 사용하지만 붉은 고정 작업물의 **보이는 표면점**을 검출한다. 객체 중심/전체6D pose/파지 방향/일반 YOLO 검출이 아니다.
- localization은 engine ground truth 교육 profile. scan은 실제 ray. AMCL/SLAM 성공이 아니다.
- 팔 독립성은 정착 상태에서 `joint1` 작은 오프셋 시험까지다.6축 궤적 추종·MoveIt·gripper 제어·물리 파지·들기·놓기는 미구현/미검증이다.

## 5. 현재 코드에서 반드시 확인할 개발 공백

| 항목 | 실제 현 상태 |13.6에서 필요한 작업 |
|---|---|---|
| 실행 수명 | `run_navigation_probe.py`가 READY를 약0.15wall초 발행한 뒤 NOT_READY로 회수하고 platform을 종료 | 동일 engine을 유지하는 상위 mission과 명시적 인계/회수 구현 |
| READY | `std_msgs/String`의 일회성 상태, 저장 summary는 완료 증거 | 새 세션의 live 상태·원본 관측·실제 정착을 재확인. 과거 JSON을 권한으로 사용 금지 |
| 팔 입력 | `Platform.on_parameters`의 `arm_joint1_offset`, ±0.05rad·최대5Hz·실제 정착/armed zero 필요 |6축 trajectory action·취소·결과·한계·관절 순서·명령 소유권 경계 |
| actuator 적용 | `platform_adapter.py`의 step hook가 매 step `desired_joint_pos_arm[0]`을 시험값으로 쓰고 `data.ctrl[12:18]`에 팔 목표 적용 | 새 입력과 기존 hold가 동시에 덮어쓰지 않도록 단일 적용 지점 구성 |
| 다리 | upstream 정책이 계속 다리 제어 | 팔 조작 중에도 지지 유지. torso 고정/teleport/정책 kill로 안정성 위장 금지 |
| 정착 판정 | 팔 속도/목표 오차/변위 조건까지 포함 | 팔 이동 중 정상 동작을 fault로 오판하지 않는 모드 계약. 이동 admission·작업 중 base 지지·작업 후 정착 구분 |
| IK | `approach_geometry.position_ik`는 위치만, TCP는 link7/link8 위치 중점 | 실제 TCP·grasp frame·방향 포함 운동학/MoveIt 계획 검증 |
| 허용 접촉 |13.5 engine hook는 group5 환경과 로봇 접촉을 모두 오류 처리 | 조작 단계에서만 지정 손가락/대상 접촉을 허용. 몸체/팔/탁자/다른 물체의 충돌 차단 유지 |
| 대상 물체 | `scene.py`의 vision target은 worldbody의 정적 geom | 물리 파지 과제라면 별도 opt-in 동적 body/질량/접촉/받침을 도입 |
| gripper | `joint7`, `joint8` 관측; upstream actuator `gripper`는 joint7 연결 | equality/연동/축/단위/행정/힘과 실제 개폐·접촉을 모델에서 확인 |
| planning model | MuJoCo 모델·실제 상태가 기준. 이 플랫폼용 MoveIt 설정 없음 | 일치하는 URDF/SRDF·mesh/한계·mount/TCP·planning scene·실행 연결 |

**중요:** 현 `run_navigation.sh vision ... 15`를 실행해 종료한 다음 새 팔 노드를 붙이는 것으로13.5→13.6 live 연계가 되지 않는다. READY를 발행한 바로 그 engine/session을 살아 있게 유지해야 한다. 새로운 통합 mission은 기존13.5 단독 실행의 정상 종료 동작을 보존하는 opt-in 경로로 만든다.

`position_ik`의 collision_free는13.5 후보 평가용 제한 검사다. link6/7/8과 target의 일부 접촉을 예외 처리하며 연속 궤적/전체 pose 충돌 계획을 대신하지 않는다. 그 관절 배열을 곧바로 실시간 팔 명령으로 보내지 않는다.

## 6. 실제 인터페이스와 소유권

네임스페이스는 `/ch13/reuse`다. 현재 존재하는 경로:

| 데이터/제어 | 이름·계약 |
|---|---|
| Nav2→smoother→경계→gate→정책 | `nav_cmd`→`smoothed_cmd`→`cmd_vel_raw`→`cmd_vel_safe`, TwistStamped |
| 실제3D pose/twist | `/ch13/reuse/engine_state` |
| 평면 odometry | `/ch13/reuse/odometry` |
| 실제 관절 | `/ch13/reuse/joint_states`; 다리12개 뒤 `joint1`~`joint8` |
| 관측 표면점/원본 정보 | `/ch13/reuse/observed_target`, `/ch13/reuse/vision/observation`, `/ch13/reuse/vision/health` |
| READY | `/ch13/reuse/ready_for_manipulation`; 기존 표시는 지속 인계 API가 아님 |
| 속도/수명 서비스 | `/ch13/reuse/navigation/idle`, `/ch13/reuse/platform/arm`, `/ch13/reuse/platform/reset`, `/ch13/reuse/platform/shutdown` 등 |
| TF | `reuse/map`→`reuse/odom`→`reuse/nav_base`→`reuse/base`→팔/카메라. 실제 body 높이·roll/pitch 보존 |

구현 원본:

- [platform_adapter.py](../ros2_ws/src/ch13_navigation_reuse/ch13_navigation_reuse/platform_adapter.py): engine/PD·상태·종료·시험 parameter.
- [command_gateway.py](../ros2_ws/src/ch13_navigation_reuse/ch13_navigation_reuse/command_gateway.py), [safety.py](../ros2_ws/src/ch13_navigation_reuse/ch13_navigation_reuse/safety.py), [navigation_boundary.py](../ros2_ws/src/ch13_navigation_reuse/ch13_navigation_reuse/navigation_boundary.py).
- [approach_geometry.py](../ros2_ws/src/ch13_navigation_reuse/ch13_navigation_reuse/approach_geometry.py), [scene.py](../ros2_ws/src/ch13_navigation_reuse/ch13_navigation_reuse/scene.py), [sensors.py](../ros2_ws/src/ch13_navigation_reuse/ch13_navigation_reuse/sensors.py).
- [run_navigation_probe.py](../scripts/reuse_13_5/run_navigation_probe.py), [vision_mission.py](../scripts/reuse_13_5/vision_mission.py), [native ingress](../ros2_ws/src/ch13_reuse_wire/src/ingress.cpp).

원본 촬영/목표 시각·최초 receipt·실제 DDS GID·단일 관절/TF/명령 소유권을 유지한다. 비유한 값/만료/시계 역행/소유자 중복은 fault latch, 자동 재활성화 금지다.

## 7. 신규 패키지 구성 제안

아래 이름과 API는 **새로 만들 후보**이며 현재 존재하지 않는다. 원고 확인과 M0 조사 후 확정한다.

```text
Ch13/ros2_ws/src/
  ch13_manipulation_reuse/          # mission·admission·arm/gripper 실행 경계
  ch13_piper_moveit_config/         # 정확한 플랫폼의 URDF/SRDF·planning/execution 설정
  ch13_manipulation_interfaces/     # 기존 표준 메시지로 부족할 때만 추가
Ch13/scripts/reuse_13_6/            # build·run·audit·verify·순차 인수
Ch13/dependencies/section_13_6_reuse.lock.json
Ch13/docs/{SECTION_13_6_REUSE_DESIGN_KO.md,
           SECTION_13_6_REUSE_IMPLEMENTATION_PLAN_KO.md,
           LAB_13_6_REUSE_GUIDE_KO.md,SECTION_13_6_REUSE_REPORT_KO.md}
Ch13/evidence/section_13_6_reuse/<UUID>/
```

추천 방향은 MoveIt의 표준 궤적 실행 인터페이스와 실제 engine 사이에 작은 어댑터를 두고 upstream native PD를 팔 actuator의 유일한 적용자로 유지하는 방식이다. ros2_control을 선택한다면 기존 PD와 병렬 명령하지 않는다. 두 실행 경로를 동시에 개발하지 말고 실제 버전/API/유지 비용을 M0에서 비교해 하나를 설계에 고정한다. MoveIt/Jazzy 최신 사용법은 설치된 버전과 공식 자료로 확인하고 설정/토픽을 추측해 먼저 고정하지 않는다.

공유 코드 변경이 필요하면 작은 재사용 hook/opt-in 모드로 처리하고 이유·기존13.5 영향·회귀를 기록한다. 전체 플랫폼 bridge나 보행 루프 복제는 피한다. 기존 v3 freeze/과거 evidence는 그대로 보존하고, 변경 소스는13.6용 새 freeze와 설치 감사를 사용한다. 수정본을 기존114파일과 일치한다고 주장하지 않는다.

## 8. 후속 개발 순서와 완료 조건

### M0 — 명세·보존·모델/제어 계약 조사

- 적용 AGENTS·실제 git/dirty/원격·소유 프로세스 확인,13.6 원고 확보. 기존 실패/사용자 문서 보존.
- 기준 `58fd73ea` 또는 이 인계 문서만 추가된 후속 commit에서 새 브랜치 `feat/ch13-section-13-6-manipulation`로 격리한다. 동명 원격이 있으면 고유 접미사. 임의 stash/clean/reset 금지.
- upstream 모델, joint1~8, gripper equality/tendon/actuator, 한계·단위·TCP·mount·정지 중 팔 자세 범위 조사. MoveIt/추론/ROS 의존성과 자산 라이선스·hash 기록.
-13.6 원고의 최소 필수 시나리오와 교육용 수치를 사전 정의한다. 조작 안정성이 새 보행 학습을 요구하면 범위를 재설계하고 근거를 보고한다.

완료: 구현할 원고 범위·플랫폼 계약·실행 경로와 작은 부품 시험 계획이 문서화됐다.

### M1 — 동일 engine의 접근→작업 인계 유지

- 기존 READY/종료 흐름을 읽고 상위 mission 수명을 설계한다. session/소유 goal/원본 관측 식별자와 실제 terminal·정착을 함께 확인한다.
- 정착 후 계속 zero를 유지하며 live 관측과 RX/physics를 살린다. 만료 시 READY를 회수하고 팔 admission 거절.
- 최소 시험: 정착 전 거절, 과거 session READY 거절, 새 goal/취소/만료로 인계 회수, 한 engine 정상 회수.

완료: 팔을 아직 움직이지 않아도 같은 살아 있는 engine에서 작업 권한 인계·회수가 관찰된다. “이전 summary가 PASS”로 대체하지 않는다.

### M2 — 작은 팔 궤적과 gripper 실행 경계

- 표준 trajectory action 등의 정확한 wire 계약,6축 순서/시간/속도·가속도/한계/취소/결과와 단일 소유권 구현.
- 정착 후 작은 관절 범위부터 실제 추종. 가짜 controller/목표 joint_states 없이 engine의 실제 q/qd/force로 판정.
- 팔 이동 중의 base 안정성과 팔 목표 hold/최종 정착을 분리한다. fault/cancel 때 마지막 유효 자세 hold 또는 검증한 정지 방식 사용; 무조건 수납/torque0 금지.
- gripper 단위·방향·실제 개폐·연동을 별도 확인. 이름만 보고 joint8에 독립 명령 금지.

완료: 작은 실제6축 궤적과 취소/입력 손실/중복 소유자에 안전한 종료를 확인했다. 이 단계는 파지 성공이 아니다.

### M3 — 정확한 MoveIt 모델과 실제 궤적 실행

- MuJoCo↔planning model의 FK/TCP/축/한계/메시/팔 mount 대조. 실제 body TF를 기준으로 계획 장면을 갱신한다.
- MoveIt가 TF/joint_states를 중복 소유하지 않도록 한다. 움직이는 base를 임의 고정 world TF로 덮지 않는다.
- collision-aware 계획→M2 실제 controller→실측 도달을 검증한다. plan-only/demo/fake hardware와 실제 실행 결과를 분리한다.
- 사전 정의한 도달 가능/불가·충돌 경로 거절·취소 시나리오로 확인한다.

완료: 단순 위치 IK가 아닌 원고가 요구한 pose/충돌 계획을 실제 팔이 추종한다.

### M4 — 원고가 요구하는 조작 과제

물리 picking이 필수라면 여기서 동적 물체/받침/개폐·접근·접촉·들기·필요 시놓기 순서를 구현한다. 시각 피드백이 필수라면 촬영→과거 TF→목표 보정→재계획/제어의 실제 루프와 만료·취소를 검증한다. 공개 모델의 힘/마찰/팔 동작 범위로 가능한지 먼저 작은 실험으로 판별한다.

기존 vision target은 정적 geom이므로 손가락을 닫아도 들 수 없다. 동적 대상의 opt-in 장면 변경과 해시를 기록한다. 대상의 실제 움직임은 인수 도구의 정답 측정에만 쓰고 비전 입력으로 위장하지 않는다. 물체를 손에 weld/teleport하거나 planning scene attach만으로 실제 파지를 선언하지 않는다. 가상 부착 교육 profile을 택한다면 물리 파지와 별도 이름·결과로 명시한다.

현재 힘 cap은 다리 hip/thigh23.7Nm·calf45.43Nm, 팔 앞3축32Nm·뒤3축8Nm, gripper0.5N이다. 가능한 하중을 이 값으로 자동 단정하지 않는다. 특정 물체/질량/마찰·파지 방향과 실제 측정을 명시한다. 성공을 위해 조용히 cap·질량·접촉을 바꾸지 않는다.

### M5 — 동결 인수·실습 가이드·게시

- source/install/model/policy hash와 수치/시나리오를 최종 실행 전에 동결한다. 교육용 기본은 필수 시나리오 각1회, 반복 강건성은 별도 확장.
- 정상 실행, 도달 불가/충돌 거절, 취소, 입력/관측 손실, 중복 소유자, 안전 정착·종료를 검증한다. 원고에 파지가 있으면 실제 개폐·접촉·정해진 높이/유지 시간·물체 상대 이탈/낙하 기준을 사전 명시한다.
- 변경 영향에 맞춘13.5 회귀를 수행한다. 실행기/센서/정책/PD/종료를 공유 수정했다면 실제 접근·취소·정지 회귀가 필요하다. 전수 matrix는 동결 후 수행하며 불변 검사 반복으로 시간을 쓰지 않는다.
- 가이드는 다운로드→의존성→build→터미널 환경→각 소절 명령→기대 결과→실패·종료 판독까지 제공한다. 원고대로 따라 할 수 있어야 한다.
- 단계별 `M0_REPORT_KO.md` 등 보고서를 남기고, 선택 파일 commit/non-force push 후 실제 remote SHA를 대조한다. 실패/미검증/교육 profile의 제한을 보고한다.

## 9. 새 창의 첫 확인 명령

아래 PowerShell은 읽기 전용이다. 저장소 경로를 확인하고 실행한다.

```powershell
Set-Location 'C:/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse'
git status --short
git branch --show-current
git rev-parse HEAD
git remote -v
git ls-remote origin refs/heads/feat/ch13-section-13-5-reuse-r2-20261102
```

실제 소유 engine/process/lock을 확인하고 정상 회수한 뒤 격리한다. 현재 clean이라는 이유만으로 checkout/강제 복구하지 않는다. 이미 소유 실행이 있으면 정상 종료 수명을 먼저 처리한다.

기존 WSL 추론/설치 경로는 다음과 같았다. 후속 확인 없이 존재/버전/자기 소유를 단정하지 않는다.

```text
WSL: Ubuntu-24.04
venv: /home/jinho/ch13_reuse_iit_d010212_venv
13.5 installed build: /home/jinho/ch13_reuse_r5_build
external assets: <repo의 상위>/upstream-iit-locomanipulation-d010212
engine lock: <repo의 상위>/ch13_reuse_engine.lock
```

13.6은 별도 `CH13_REUSE_BUILD`와 증거 경로를 사용한다. 기존 R5 install/underlay·upstream 원본을 덮지 않는다. `build_r2.sh`는 기존 세 패키지만 선택 빌드하므로 새 패키지가 자동 포함되지 않는다. 새 build/launch/audit 도구에서 의존성을 명시한다. ROS CLI는 시스템 Python으로 실행하고 추론 venv를 전역 activate하지 않는다. 기본 명령 준비법은13.5 가이드에 있다.

## 10. 보존·권한·효율

- `sources/`, Ch01~12, 외부 checkout/underlay 원본은 읽기 전용. 사용자 `SECTION_13_4_DEBUGGING_LESSONS_KO.md` 수정·선택 stage 금지.
- 기존13.5 PASS/FAIL·gate/freeze/evidence를 수정해13.6 성공으로 만들지 않는다. 새 namespace/revision/UUID와 증거 manifest를 사용한다.
- 원본 촬영·최초 receipt·과거 TF·관측 age300ms·과거 TF100ms 계약을 보존한다. 새 trajectory의 제어주기는 별도로 설계하되 기존 비전 목표 갱신/팔 명령5Hz 계약과 양립하게 구분한다. 오래된 header를 now로 바꿔 수명 연장 금지.
- action 취소 ACK와 실제 terminal, 실제 정지와 프로세스 소멸을 분리한다. worker/renderer/RX join·부모/engine 정상 종료·잔여 검사까지 수행한다.
- 엔진은 순차 실행. 실행 중 build/pytest/대용량 분석을 병행하지 않는다. 최소 부품 시험으로 원인을 줄인 뒤 실제 engine을 돌린다.
- 같은 실패 계열이 두 번의 최소 수정 후에도 남으면 구조를 검토한다. 무제한 gain/마찰/질량 탐색으로 되돌아가지 않는다.
- 활성 작업/설치 대기/실행/분석 시간을 구분한다. 대표 성공/실패를 먼저 pin하고 기타 증거는 기존 보존 정책에 따라 작게 유지한다.
- 시스템 권한·드라이버·전역 시간·외부 환경 변경을 기존 코드 개발 승인으로 확대하지 않는다. 설치가 필요하면 구체적 패키지와 영향을 밝힌다.

## 11. 새 창에 붙여 넣을 시작 요청

> `Ch13/docs/HANDOFF_SECTION_13_6_MANIPULATION_2026_11_03_KO.md`를 먼저 읽고, 이 공개 Go2+Piper 패키지를 기반으로13.6 실습 패키지 개발을 시작하라. 단일 작업자로 진행하고 구현 계획 실행에는 superpowers:executing-plans를 적용하라. 먼저 적용 AGENTS·git/원격·실행 소유 상태를 확인하고13.6 원고와 M0 인터페이스 조사부터 진행하라. 원고가 없으면 필수 조작 과제 확인을 요청하면서 독립적인 코드·모델 조사를 진행하라.13.5의 일회성 READY와 종료, joint1 시험 입력, 정적 target/충돌 차단을 실제로 대체할 연결 설계를 먼저 작성하라. 기존13.5 증거와 외부 원본을 보존하고 새 브랜치·별도 build·새 evidence로 진행하라. 단계별 보고서·검증·선택 commit/push를 수행하되 현재 인계 문서를13.6 구현 완료로 해석하지 마라.
