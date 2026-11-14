# Physical AI ROS 2 교재 — 101 LAB 증거 통합 및 출판 범위 검수 보고
**기준일:** 2026-11-14 KST  
**기준 원격:** `silverbjin/Pysical_AI_ROS2` / `main` (작업 시작 `33df002a5a9a52800ef3f72c3d4a382161153336`)  
**총괄:** [GitHub Issue #118](https://github.com/silverbjin/Pysical_AI_ROS2/issues/118)  
**제외:** [Ch10 Issue #123](https://github.com/silverbjin/Pysical_AI_ROS2/issues/123), 명시적 HOLD. **어떠한 Ch10 동적 실행·IK 수정·보행 시험도 하지 않음.**

> **현재 판정: `DOCUMENT_AND_SCOPE_RECONCILIATION_PASS / FULL_101_LABS_RUNTIME_NOT_ACCEPTED`.**
>
> 도서 문서가 모두 존재한다는 사실과, 내용의 물리·ROS 작동이 모두 검증됐다는 사실은 다르다. 이 PR은 이미 성공한 ROS/Gazebo/MuJoCo 시험을 재실행하지 않고 **독자에게 표시할 실제 능력과 재현 증거의 차이**를 해소하는 출판용 범위 정합 작업이다. `101/101 RUN PASS`를 승인하거나 #118을 거짓 종료하지 않는다.

## 1. 명확히 확인한 실습 수의 의미

- **13장 98개 번호 절(§1.1~§13.8)**. 실제 기본 가이드 98개 존재.
- **중복 번호가 아닌 Ch13 추가 가이드 3개**를 포함한 전체 실제 Markdown 실습 가이드 문서는 **101개**. 이 숫자는 `ci/manifest.json`의 장별 최소 수(합계 97개)와 혼용하면 안 된다.
- 실습 번호에만 의존하면 Ch13 13.6·13.7·13.8의 실제 파일명 `LAB_13_6_REUSE_GUIDE_KO.md`, `LAB_13_7_BT_GUIDE_KO.md`, `START_HERE_13_8_KO.md`를 '없음'으로 잘못 세므로, `ci/book_acceptance_matrix.py`가 실존 파일로 직접 매핑한다.
- **코드 감사 보고서와 단순 링크 검사는 전체 런타임 PASS가 아니다.** 현재 CI는 13장 L0 문서 링크/울타리 확인과 별개로, 98절을 `SCOPED_PASS / EVIDENCE_REVIEW_REQUIRED / BLOCKED / FAIL / HOLD`로 구분하여 CSV/JSON을 발행한다. PASS 근거는 커밋·실제 run·Artifact 또는 명시적으로 연결된 원본 native JSON만 활용한다. 일반 문서의 '예상 결과'는 실측하지 않은 것으로 남긴다.

**실측 증거 매트릭스 소스:** `ci/book_acceptance_evidence.json`. **생성기:** `ci/book_acceptance_matrix.py`.  
공개 L0 워크플로의 동일 Artifact에 `book-101-matrix/acceptance_matrix.csv`, `acceptance_matrix.json`, `SUMMARY.md`가 보존된다. 모든 CI 성공 기록은 해당 소스 SHA/가이드, 선택 범위와 함께 표기한다. 독자가 보는 '통과'라는 문구에서 **SCOPED** 수식어를 생략하지 않는다.

## 2. 출판 전 코드-설명 불일치 처리

| 대상 | 실제 소스/실측 사실 | 최종 교재용 처리 | 미완료 |
|---|---|---|---|
| Ch07 7.2~7.6 | 카메라·Depth·TF·그리퍼 등 각각 별도 실제 CI PASS | 각 증거의 입력 조건(가시 표적, synthetic 입력, 이중 CI)을 명시하여 독립 부분 실습으로 안내 | 광학 색상 정렬, GUI, 실물 접촉 파지는 별개 |
| **Ch07 §7.7** | `object_detector`는 `/camera/target_pixel` 발행, `mission_controller`는 이를 구독하지 않고 `target_object` TF 대기, `move_arm`은 고정 위치. `setup.py`에는 `mission_controller` console entry 없음 | **BLOCKED: 미완료 종합 미션**, `LAB_7_7_GUIDE_KO.md`에 미션의 정확한 누락 계약과 정상/실패 체크리스트를 공개. 구성 요소 PASS의 합을 파지 성공으로 포장하지 않음 | detector→실제 3D target→MoveIt→그리퍼→world object pose 이동을 **한 세션**에서 검수할 때만 정식 PASS |
| **Ch08 §8.7** | Frozen PPO 10회 실제 목표 성공 **0/10**, 평균 최종 거리 **0.432753m**. 새 EE 속도 계측도 최소 접근 이후 목표 반대로 움직임 확인 | **평가 기능 SCOPED_PASS / 정책 성능 FAIL**을 가이드 예시·학습 과제에 명시. 기존 ZIP·보상 설정 불변 | 새로운 개선 정책 훈련+별도 holdout 목표 성공 없음. `RecordVideo` RGB 미구현 |
| **Ch11 §11.7** | 원본 `/slam_toolbox/save_map` 응답 `255` FAIL, 공식 Nav2 Map Saver 15초 CLI는 실제 YAML/PGM PASS (138×137/비미확인 1,500셀) | 학생의 기본 저장 명령은 **검증된 15초 Nav2 CLI**로 제시; 바뀐 작업 디렉터리에서 `BOOK_REPO` 절대 경로 유지; 10초 기존 래퍼와 원본 서비스 결과를 따로 명시 | 원본 service 실패 원인 [#130](https://github.com/silverbjin/Pysical_AI_ROS2/issues/130) 유지, 지도 정확도·재로딩·완전 자율탐사 NOT_RUN |
| **Ch12 §12.4/§12.8** | 저장소 안의 native `ppo_runs/cli/result.json`은 64-step PPO 파라미터 갱신 PASS / 성공률 0%; §12.8 과거 MuJoCo/Gazebo 별도 JSON은 401/334 active samples·48관측·12 정책 관절 실제 ROS 연결 PASS | **과거 동결 시뮬레이션 통신·훈련 파이프라인**으로만 SCOPED_PASS 증거 연결, 미수행 전체 성능이나 현재 main 신규 CI를 주장하지 않음 | 장기 보행·목표 도착·장애물회피 일반화, 최신 main 재빌드·실기 인정 미실시 |
| **Ch13 13.5~13.8** | 원본 R5/M4/v53/13.7 JSON에 당대 source hash + 94 외부자산 + 대표 실제 성공·실패 있음 | 독자 clone은 최신 **main**을 사용하도록 수정. 개발 feat 브랜치 안내는 이력으로 분리. 13.8 **basic 이동·관측·종료**와 **full pick/carry/place 미완료**를 명확히 분리 | 외부 자산 hash와 최신 main의 새 WSL2 clone 인수는 MANUAL_REQUIRED, 일반 연속 미션 full PASS 없음 |
| Ch09 #171 | 원본 네 발 총 하중 약 117.6N 실제 Gazebo ground contacts scoped PASS | '정지 기립 발 접촉'으로만 기술 | 동적 슬립 속도, 실측 마찰계수는 심화 NOT_RUN |
| Ch10 #123 | URDF 링크 0.25m vs IK 0.20m 결함, 기존 실패 증거 | **HOLD** · PASS로 표시 금지 | 사용자 HOLD 해제 전 어떤 수정/보행 인수도 금지 |

## 3. 이번 검수 과정에서 성공 시험을 다시 실행하지 않은 증거

동일 runtime을 반복하지 않고 과거 보존된 실제 [Ch04 §§4.3/4.4](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43374148019) TF/리스너, [Ch05 §5.6](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43378792564) Gazebo 실제 사인파, [Ch08 §8.8](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43362183693) Python 입력 fail-closed의 성공 Artifact를 별도 다운로드하여 매트릭스에 후속 연결했다. 원본 Ch12 §12.4/12.8과 Ch13 §13.7 native JSON도 저장소 직접 읽기로 재확인했다. **새 CI는 L0/JSON matrix/unit tests/Markdown link 검사만 실행하며, 기존 Ch02/Ch12 파일럿 Job은 SKIPPED이다.**

## 4. 즉시 출판 인수와 실제 미완료의 분리

**출판 가능 범위:** 기존 성공이 이미 확보된 부분 실습과 실패를 학습하는 진단 실습의 **구체적 범위**. 학생이 원문 명령을 실행했을 때 기대 결과가 실측과 다른 항목은 예시 또는 미완료로 표시한다. `EVIDENCE_REVIEW_REQUIRED` 절은 **기존 Artifact 재대조 전까지 전체 실습 PASS로 전환하지 않음**.

**전체 교재 runtime 101/101 PASS:** **현재 달성 불가.** Ch10 8개 HOLD, Ch07 7.7 미션 연결 결손, Ch08 원본 PPO 성능 FAIL, 장기/GUI/하드웨어 등 원문에서 요구하는 일부 경계가 미검증이다.

**현장 인수 필요 항목:** GUI/RViz/WSLg가 학습 목표인 실습만 한 세션에서 재현; Ch13 최신 main과 94 외부자산 새 clone 설치·SHA; 필요 시 물체의 시각 인식과 실제 world pose 기반 파지. 원격 public headless CI에서 성공한 Gazebo/ROS 숫자 측정은 다시 실행하지 않는다.

**잔여 개발 순서:** (1) Ch07 §7.7 미션 목표 연결을 안전하게 분리 구현해 실제 world object pose로 판정. (2) 원본 PPO 0/10은 교육 목표 '평가·실패 분석'으로 제한하거나 **새 별도 정책**을 학습하여 holdout 목표 성공을 증명. (3) Ch11 service 이슈를 교재 선택 기능으로 유지하고 공식 CLI를 기본. (4) Ch12/13 기존 source freeze→최신 main 비교 증거만 부족한 경우 추가. (5) 최종 WSL2 GUI 및 Ch13 설치 Owner 판정 후 범위 한정 출판 인수 승인.

## 5. Issue 정책

- **#118 OPEN:** 모든 번호 절에 연결된 실제 실행 결과를 구분하며, `101/101 실행 PASS`로 종료하지 않는다.
- **#123 OPEN / HOLD:** Ch10 실제 결함과 사용자 보류 유지.
- **#130 OPEN / 원본 SERVICE FAIL:** 공식 CLI를 별도로 기본 대체.
- **#171 OPEN / NOT_RUN:** 동적 지면 마찰·슬립은 선택 심화.

**검수 최종 표현:** “101개 가이드 문서·링크 인벤토리 정상, 실제 실행은 성공 증거 범위만 SCOPED PASS. 원본 실패·차단·HOLD는 이력과 출판용 주의사항으로 보존. 전체 자동/물리 런타임 인수는 아직 완료되지 않음.”

이 보고서에 포함된 과거 수치/CI는 출처를 가진 **기존 증거의 재해석**이며, 이번 단독 신규 ROS/Gazebo/MuJoCo 실행이 아니다. 
