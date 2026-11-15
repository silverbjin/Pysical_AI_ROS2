# ROS 2 도서 실습 개발·디버깅·CI 실행 표준 (승인본)

- **문서 ID:** BOOK_ROS2_DEV_DEBUG_CI_STD_V1
- **시행일:** 2026-11-15
- **적용 범위:** `silverbjin/Pysical_AI_ROS2`의 Ch01~Ch13 도서 실습 코드, 검수기, 공개 GitHub Actions; 특히 Ch07 §7.7 Issue #173/#181
- **기준:** Issue #118 총괄 검수, [Fast Loop 지침](BOOK_REVIEW_FAST_LOOP_STANDARD_20261115_KO.md), [P1 준비형 이미지 안내](BOOK_G04B_PREPARED_IMAGE_DIGEST_GUIDE_20261115_KO.md)
- **승인 범위:** 개발·디버깅 방법론 및 단계별 CI 운영 변경. **미승인:** 임의의 물리 L2 Goal, 인수 게이트 완화, Draft PR 병합, Owner WSL2 실행
- **현행 인수:** G00–G04A 기존 성공 **NOT_RERUN** / G04B **BLOCKED** / G05 **NOT_RUN** / Ch10 **HOLD**

> 본 문서는 개발자가 다음 실험을 선택하는 **실행 규칙**이다. CI SUCCESS 표시만으로 기능을 완료했다고 판정하는 문서가 아니다.

## 1. 운영 목적과 비목표

**목적:** 초기에 틀린 전제와 잘못된 판정기를 발견해, 사용자가 반복해서 GitHub CI를 실행하거나 WSL2에서 디버깅할 필요를 최소화한다. 이미 성공한 소스·증거·해시를 보존하고, 새 실패 경계만 좁힌다.

**비목표:** 통과율을 높이기 위한 테스트 제거, 안전 허용 오차 완화, 더미/가짜 접촉, 물체 attach·teleport, 강제 PASS, 실습 코드 기능 범위의 무단 축소, Ch10 자동 재개.

**프로젝트별 고정값:** ROS 2 Jazzy / Gazebo Harmonic(Sim8), 기 검증된 GHCR image digest `ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f`. 준비형 새 이미지는 실제 빌드·게시·digest 검증 및 CI/Owner 일치 검증이 완료되기 전까지 **후보**다.

## 2. 개발 방법 선택 기준

| 대상 | 기본 방법 | 어디까지 자동화하는가 |
|---|---|---|
| 알고리즘, 수치 계산, FK/IK, TF, 좌표 변환, 상태 판단 | **선택적 TDD** | 결정적 입력/출력 단위시험으로 RED→GREEN→REFACTOR |
| ROS 2 토픽·서비스·Action·QoS·Lifecycle·FJT 계약 | **Contract-First + 통합시험** | 모의 인터페이스 확인 후 필요한 실제 ROS 관측만 |
| URDF/Xacro/SDF 구성, 관절축, 베이스 고정, 모델 프레임 | **Architecture-First + 불변식 검사** | 실제 모델 구성·좌표 정의부터 검증 |
| Gazebo 동역학, 관절 구동, 센서, 마찰·접촉·파지 | **가설 기반 실험** | 한 개의 반증 가능한 가설과 실제 Gazebo L2 1회 |
| 통합 Pick-and-Place, 최종 배치 ROI, 종료 복구 | **증거 기반 인수** | 단계별 실측 + 같은 세션의 최종 원본 검토 |

물리적 비결정성을 제거하려고 전체 시스템을 TDD 테스트로 덮지 않는다. 반대로 물리적 PASS가 필요한 기능을 단위시험 PASS만으로 완료 처리하지 않는다.

## 3. 모든 작업에 적용하는 실행 흐름

1. **S0 범위 고정:** Issue/절, 실제 설명 기능, 원격 `main`과 작업 브랜치 HEAD, 마지막 정상 원본·실패 원본의 SHA/Artifact ID, 보류 범위를 조회한다. 현재 대화 내용만으로 최신 원격이라고 간주하지 않는다.
2. **S1 아키텍처·검수기 검토(P0):** URDF 관절/고정·로봇 모델 루트, SDF 생성물, `TF`의 world/model/link frame, ROS clock, controller source, 물체 및 지형의 실제 collision geometry, 측정 단위와 수용 오차부터 확인한다.
3. **S2 최초 실패 경계 추출:** 기존 Artifact를 **오프라인**으로 읽고 시간 동기화하여 `goal → reference → feedback/error → hardware command → native joint/pose → contacts → object ROI` 사슬 중 최초로 어긋난 단계 하나를 기록한다. 로그 문자열보다 원본 수치가 우선한다.
4. **S3 인과 가설:** 원인 후보와 반증 조건을 적는다. **변경 요인은 한 가지**, 반드시 다음 시험에서 바뀌어야 할 수치·시간·관측 지점을 사전 정의한다. 기존 raw로 답이 나면 코드를 수정하거나 Gazebo를 실행하지 않는다.
5. **S4 대상 L0:** 변경된 파일에 필요한 `bash -n`, `py_compile`, 관련 `unittest`, YAML/URDF/SDF 구조 검사만 수행한다. 독립적인 ROS·물리 전체 시험을 함께 실행하지 않는다.
6. **S5 필요한 경우 L1:** ROS 2 인터페이스나 controller 연결을 실제로 변경한 경우에만 해당 인터페이스의 최소 실측 검증을 수행한다. L0만으로 물리적 성능을 주장하지 않는다.
7. **S6 명시적 L2 승인 및 한 번의 Gazebo CI:** L0/L1과 원본 인과 분석이 완료된 **동일 SHA**에 대해 시험 목적·예상 변화·실패 중지 조건을 기록하고 실제 Gazebo 시험을 1회 호출한다.
8. **S7 원본 감사:** 예상 변화, 첫 실패, 남은 위험, 원본 Artifact ZIP 해시, 실제 물체 최종 ROI를 확인한다. 실패하면 FAIL 유지. 새로운 증거가 있는 경우에만 S2로 되돌아간다.
9. **S8 정리:** REFACTOR(동작 불변)→REVIEW→COMMIT; 결과와 근거를 Issue와 **하나의 활성 PR**에 기록한다. L2 결과를 감사하기 전에는 L3·Owner 인수로 넘어가지 않는다.

### 공통 중단 규칙

- 같은 실패를 **새 정보 없이 2번** 확인하면 추가 시험을 중단하고 S1/S2의 모델·좌표계·판정기·계측을 재검토한다.
- 원본 증거가 없거나 SHA/digest가 불일치하면 **판정 보류**. 다른 실험의 성공을 현재 HEAD로 옮겨 적지 않는다.
- 동작과 무관한 계측 변경마다 L2를 다시 실행하지 않는다. 필요한 값은 가능한 한 하나의 read-only 계측으로 일괄 수집한다.
- 시험이 ROS/Goal 실행 전 패키지 설치·컴파일·import 오류로 끝나면 **환경 또는 계측 실패**로 기록한다. 이를 물리 가설의 RED 증거로 사용하지 않는다.
- 센서의 `contact force > 0`와 Controller `SUCCEEDED`는 관측치이지 물리적 인수의 충분조건이 아니다.

## 4. 단계별 CI 운용 계약

| 단계 | 자동/수동 | 진입 조건 | 검증·출력 | 성공의 의미 |
|---|---|---|---|---|
| **L0 정적/단위** | 관련 PR 수정 시 자동 | 변경 파일·의존성 명시 | hash, bash/Python/YAML/모델 불변식, 대상 TDD | 코드 계약만 만족; **Gazebo 미실행** |
| **L1 ROS 통합** | 관련 인터페이스 수정 시 선택 | L0 PASS, 명시한 ROS 변경 | 실제 `/joint_states`, action/result, QoS/lifecycle | 해당 ROS 인터페이스 범위 확인 |
| **L2 Gazebo 물리** | **명시적 승인형** | 첫 실패·가설·L0/L1·동일 source SHA/digest 확인 | 한 번의 실제 Gazebo + FJT, native pose/contact, raw custody | 범위 내 물리 검증. FAIL 시 인수 유지 |
| **L3 기능 통합** | L2 증거 감사 후 제한적 | 물리 세부 항목 충족 | 같은 세션 RGB-D→MoveIt→파지·운반·배치·복구 | 요구 기능의 실제 통합 재현 |
| **Owner WSL2** | 최종 현장 인수 | 해당 공개 CI L2/L3 PASS 및 정확한 SHA | 동일 조건에서 실제 GUI/시연·종료 | 최종 인수 기록; 개발용 디버그 아님 |

### 4.1 문서 CI 분리

- `Book Lab Acceptance`: 문서, 가이드, 명시된 검수 매트릭스와 validator만 실행한다. 광범위 `ci/tests/**`, `Ch[0-1][0-9]/**` 트리거로 ROS·물리 시험을 우연히 가져오지 않는다.
- 문서 runner에서 모든 `ci/tests`를 탐색해 `vision_basics` import 실패를 유발하던 기존 패턴은 금지한다.
- 전용 Ch02/Ch12 파일럿은 수동 실행 옵션으로 유지한다.

### 4.2 G04B 물리 CI의 실제 승인 경로

- 활성 PR: [#202](https://github.com/silverbjin/Pysical_AI_ROS2/pull/202). PR `opened/reopened/synchronize` 시 **`contract-preflight` L0만** 실행한다.
- 현행 workflow의 L2는 `pull_request`에 **새로운 `g04b-physics-once` 라벨이 추가된 이벤트**에만 실행한다(또는 배포 가능한 브랜치의 별도 수동 dispatch). 라벨이 이미 붙어 있다는 사실만으로 모든 synchronize가 L2를 실행하지 않는다.
- 라벨은 원인 가설, 단일 시험 범위, 동일 SHA를 확인한 후 명시적으로 부여한다. 실패해서 자동 재시도하거나 자동으로 라벨을 다시 붙이지 않는다. GitHub Actions의 수동 dispatch가 어느 브랜치에 가능한지는 실제 workflow 등록 상태로 확인한다.
- L2는 기존 원본 동적 물체, 실제 Gazebo 물리, 엄격한 목적지 ROI·정지·해제 검증, Artifact 업로드를 그대로 수행한다.
- **`contract-preflight SUCCESS + dynamic-physics-grasp-only SKIPPED` = L0 PASS / G04B BLOCKED.** 전체 워크플로 UI의 초록색을 물리 PASS로 쓰지 않는다.

### 4.3 환경·이미지 비용(P1)

- 동일 시뮬레이션 안에서 매번 실행하는 `apt-get update/install` 대신 **한 번만 구축한 준비형 이미지**를 목표로 한다.
- `ci/docker/Dockerfile.book-g04b-prepared` / `build_book_g04b_prepared_runtime.sh` / `check_book_g04b_prepared_runtime.sh`는 **후보**다. 신규 digest의 실제 빌드, 패키지·ABI 검증, 게시, CI/Owner 소스·이미지 일치가 완료될 때까지 원본 검증 이미지는 바꾸지 않는다.
- 캐시는 `source SHA + ROS distro + image digest + 의존성 lock`이 일치할 때만 사용한다. 기존 성공 Artifact는 캐시와 별도로 보존한다.
- 배포 시 태그가 아니라 `image@sha256:...`를 동일하게 고정한다. CI/WSL2의 실행 진입점과 로그/종료/증거 규격을 동일하게 유지한다.

## 5. G04B 물리·관절 디버깅의 증거 사슬

**첫 실패부터 확인**하며 통과한 단계를 불필요하게 재실행하지 않는다.

| 순서 | 확인 데이터 | 불일치 시 먼저 의심할 경계 |
|---|---|---|
| 1 | Goal UUID, 목표 관절, FJT `desired.positions` | 잘못된 action/관절명/목표 |
| 2 | JTC `reference`, `feedback.actual`, `error` 및 타임스탬프 | 컨트롤러 목표/실제 피드백 |
| 3 | ros2_control hardware command, command interface 소유권 | JTC→GazeboSimSystem 전달 |
| 4 | native Gazebo `JointState`·관절 위치/속도/하중 | command→물리 관절 동작 |
| 5 | `T_world_model × T_model_link × T_link_collision` 및 물체 world pose | 실제 공간 관계·좌표 변환·베이스 회전 |
| 6 | 동일 시각 native contacts, 접촉쌍/시각, 필요 시 ECS read-only | 접촉 신호 갱신/진짜 기하학적 접촉 |
| 7 | 물체 실제 상승·홀드·운반 중 custody | 진짜 물리 파지의 지속 |
| 8 | 해제 및 최종 ROI / 정착 안정성 | 도서 Pick-and-Place 최종 기능 |

**주의할 실제 사례:** #195–#201을 비교할 때 SceneBroadcaster의 **model-relative link Pose**를 world 좌표로 잘못 취급해 손가락-원통 간격을 과대평가한 적이 있다. 반드시 로봇 모델 world 변환과 회전을 적용하여 다시 산정한다. 원본 URDF에서는 `world_to_base_joint`가 주석 처리되어 있어 물리 베이스 이동 가능성을 먼저 확인한다.

**2026-11-15 첫 미해결 경계:** #202 실제 Gazebo [Run #43696129194](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43696129194), Artifact `14154511511`에서는 **Finger 1의 최초 2mm FJT actual≈0, Finger 2 actual≈2mm, Action ABORTED/error -5**로 멈췄다. 이 세션에서는 고단 운반·최종 ROI가 실행되지 않았으므로 해당 실패의 다음 가설은 **Finger 1 초기 구동 전달 경계**로 한정한다. 베이스 고정이 전체 물리 문제를 해결했다고 추정하지 않는다.

## 6. 원본 증거와 인수 판정 계약

**실행 ID마다 기록할 필수 필드:** source commit SHA, PR/branch, CI Run/job, Docker image digest, command line, ROS_DOMAIN_ID/GZ_PARTITION, 원본 Artifact ID·ZIP SHA256, 최초 실패 단계와 시각, 해당 구간 `/clock`, FJT 목표/실제/오차, `/joint_states`, native model/link world pose, collision geometry/contacts, 물체 lift/hold/carry/release/ROI 결과, 종료 상태.

- 기존 수용 증거의 정확한 SHA가 동일하지 않으면 새 버전에 대한 PASS를 자동 주장할 수 없다.
- `BOOK_LAB_REPRODUCED`: 본문의 명령·관찰을 재현한 범위만 표현. 물리 운반 완료를 의미하지 않는다.
- `G04B_BLOCKED`: 관절·접촉·상승·운반·정착 중 필수 단계 미충족 또는 미실행.
- `G05_NOT_RUN`: 동일 실행의 실제 RGB-D→MoveIt→파지 통합 미실시.
- `CH10_HOLD`: 사용자 보류 명령. 다른 성공으로 대체 불가.
- 확정 불가능하면 `UNKNOWN`/NOT_RUN, 증거가 모순되면 `CONFLICT`/BLOCKED. 임의 `ACCEPTED` 금지.

### 6.1 최소 실험 기록 템플릿

```text
ISSUE_AND_SECTION:
BASE_MAIN_SHA:
PR_HEAD_SHA:
PREVIOUS_ACCEPTED_SHA_AND_ARTIFACT:
FIRST_FAILED_BOUNDARY:
OBSERVED_NATIVE_DATA_AND_SIM_TIMESTAMP:
ONE_HYPOTHESIS:
PREDICTION_AND_DISCONFIRMATION:
SINGLE_CHANGED_FACTOR:
L0_RESULT_AND_RUN:
L1_RESULT_IF_REQUIRED:
L2_EXPLICIT_APPROVAL_EVENT:
L2_RUN_ID_IMAGE_DIGEST:
RAW_ARTIFACT_ID_SHA256:
EXPECTED_VS_ACTUAL:
FIRST_FAILURE_OR_ACCEPTANCE:
NEXT_STEP_OR_STOP_REASON:
ACCEPTANCE_STATE:
```

## 7. PR·리뷰·완료 운영(P3/P4)

- 이슈 하나에 **활성 개발 PR 하나**를 원칙으로 한다. 기존 #180~#202 Draft와 증거는 임의 병합·삭제·닫기·force push하지 않는다.
- 기존 Issue #181의 read-only 실험 결과와 최초 실패 데이터를 재사용한다. 새로운 가설마다 Draft PR을 새로 만들기보다 PR 안에서 commit과 증거 표로 추적한다.
- 리뷰 기준: **원본 실패 한 개를 인용하는가? / 한 가지 원인만 바꾸는가? / 비교 가능한 CI 원본인가? / 예상 관측이 사전 정의됐는가? / 다른 성공 게이트를 훼손하지 않았는가?**
- P0 도서 검수 항목과 물리 접촉 솔버 연구를 구분한다. 도서가 실제 물리 Pick-and-Place를 요구하는 경우 그 기능은 **BLOCKED로 투명하게 공개**하고 연구성 실험으로 부풀려 자동 인수하지 않는다.
- 프로세스 정책 PR [#203](https://github.com/silverbjin/Pysical_AI_ROS2/pull/203)은 Draft로 유지하며, 승인 범위 밖의 물리 변경이나 main 병합과 혼합하지 않는다.

## 8. 성능 지표와 통제

매 이슈·주간 검수 보고에는 다음 다섯 가지를 기록한다.

1. **첫 실패 확정 경과시간:** 첫 Run부터 native 신호 단절 위치 확인까지
2. **CI 비용:** L0/L1/L2별 실제 실행 횟수, 누적 runner 시간, 1 Run 준비시간 대 관측시간
3. **유효 정보량:** 새 가설이 기각/지지/원인 확정에 얼마나 기여했는지; 동일 실패만 반복한 Run 수
4. **검증 성공의 정확성:** 실제 기능 PASS와 사전검증 PASS 혼동 0건; SHA/digest 불일치 0건
5. **개발 복잡도:** 활성 PR 수, 중복 workflow 수, 실패에 새 계측/커밋/재실행이 과도하지 않은지

실측 기준선: 2026-11-12~15 전체 CI 548회, G04B 전용 89회(성공 0); 기존 물리 Run #43696129194 약 153초, 개선된 **L0 전용** Run #43703719507 약 12초. 이 수치는 **검증 범위가 다르므로 L2 성능 자체가 92% 좋아졌다고 주장하지 않는다**. 목표는 L2가 불필요한 PR 변경에서 실행되는 빈도를 줄이는 것이다.

## 9. 현재 적용된 코드와 미완료 작업

| 항목 | 코드/증거 | 상태 |
|---|---|---|
| 문서 CI의 광범위 트리거 제거 및 validator만 실행 | Draft #203, [#43703652196](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43703652196) | **L0 PASS** |
| G04B PR L0 자동 + L2 명시적 승인형 분리 | Draft #202, [#43703719507](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43703719507) | **L0 PASS / 물리 SKIPPED** |
| 준비형 Dockerfile/스크립트 정적 계약 | Draft #203, [#43703652271](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43703652271) | **정적 PASS / 이미지 미빌드** |
| 원본 Gazebo G04B 실제 최종 배치 | #202, Run #43696129194 raw | **BLOCKED** |
| 같은 세션 G05 RGB-D 통합 | Issue #173/#181 | **NOT_RUN** |
| Ch10 | Issue #123 | **HOLD** |

## 10. 새 작업 요청에 즉시 적용할 명령형 지침

> 1. 최신 원격 `main`·현재 작업 브랜치·미해결 Issue와 원본 Artifact ID/SHA256을 먼저 확인하라.  
> 2. 성공한 G00–G04A를 재실행하지 말고, 현재 첫 실패 단계의 native 데이터만 오프라인으로 비교하라.  
> 3. 로봇 아키텍처, 월드/모델/링크 좌표, SDF, 실제 컨트롤러 명령과 판정기의 정확성을 검증하라.  
> 4. 가설을 하나 정의하고 **예상 측정값/반증 기준/한 가지 변경 요인**을 기록하라.  
> 5. 변경 범위에 맞는 L0와 필요한 경우 L1을 먼저 실행하라. L0 PASS를 물리 PASS로 취급하지 말라.  
> 6. 실제 Gazebo L2가 필요한 경우에만 동일 SHA·image digest를 고정하고 승인형 단일 실행을 수행하라. 실패하면 원본 증거를 보존하고 인수 상태를 유지하라.  
> 7. 결과를 Issue #181과 활성 Draft PR에 기록하고, 새로운 정보 없는 재시도·광범위 sweep·새 PR 난립을 금지하라.  
> 8. 실제 G04B와 G05를 각각 필요한 native 증거로 검증하기 전까지 BLOCKED/NOT_RUN을 유지하고 Owner WSL2 인수를 요구하지 말라.

---

**문서 종료:** 이 지침의 채택/CI L0 성공은 G04B/G05 기능 인수와 무관하다. 최종 물리 동작의 검증 증거가 없으면 완료로 표시하지 않는다.
