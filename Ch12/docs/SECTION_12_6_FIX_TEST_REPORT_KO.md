# Ch12 12.6 — 코드 수정 및 정적 테스트 보고서 (2026-10-21)

> **범위:** 원고 12.6과 [기존 코드 리뷰](SECTION_12_6_REPORT_KO.md)의 후속 코드 보강. **브랜치:** `docs/ch12-section-12-6-review-20261021`. **PR:** [#109](https://github.com/silverbjin/Pysical_AI_ROS2/pull/109). **main 직접 Push/병합 없음.**
>
> **판정:** `STATIC_REVIEWED` + `STATIC_CONTRACT_PASS` + `PATCH_FRAGMENT_SYNTAX_PASS` (한정). **전체 파일 구문 검사, pytest, MuJoCo/ROS/Gazebo/PPO 런타임:** `NOT_RUN`.

## 1. 발견 사항과 Root Cause

- **원인·위험:** 비정상적인 LiDAR ray 결과 NaN/Inf가 64/80-D 정책 관측으로 전파될 수 있음
- **수정:** mj_ray 반환이 유한하지 않으면 normalize하기 전에 FloatingPointError로 중단
- **영향 및 호환성:** 정상 -1(no hit)와 [0,range]의 기존 정규화 처리·장애물 충돌 페널티는 유지.

## 2. 실제 수정 파일

| 구분 | 경로 | 수행 |
|---|---|---|
| 본 코드 | `Ch12/src/quadruped_rl/avoidance_env.py` | 해당 절의 입력/진단·보호 계약 최소 변경 |
| 회귀 테스트 | `Ch12/tests/test_avoidance_env.py` | `test_lidar_rejects_nonfinite_ray_before_policy_observation` 신규 작성 |
| 기존 리뷰 | `Ch12/docs/SECTION_12_6_REPORT_KO.md` | 2026-10-21 이전 정적 리뷰 증거 보존 |
| 이번 보고서 | `Ch12/docs/SECTION_12_6_FIX_TEST_REPORT_KO.md` | 수정 범위·검증 경계·후속 명령 기록 |

## 3. 정적 테스트: 실제 수행 결과

검증 기준: GitHub 원격 `main` 및 해당 기존 절별 브랜치의 UTF-8 파일을 각각 조회한 뒤 검사. **원격 브랜치의 소스가 변경됐는지, 보호 조건을 포함하는지, 기존 테스트 본문이 유지되며 신규 회귀 함수가 추가됐는지**를 프로그램으로 검사했다.

| 검증 항목 | 방법 | 판정 |
|---|---|---|
| 본 코드 변경 존재 | 원격 `main` 대비 파일 콘텐츠 비교 | **PASS** |
| 핵심 guard / 오류 기록 존재 | 브랜치 소스 내 조건·오류 문구 검사 | **PASS** |
| 기존 회귀 테스트 보존 | 기존 파일 내용 선행 부분 동일성 검사 | **PASS** |
| 신규 회귀 테스트 함수 추가 | 함수 선언 건수 및 신규 파일 내용 검사 | **PASS** |
| 변경 코드 조각 구문 | 수동 재구성한 핵심 패치 조각에 `ast.parse` + `compile` | **PASS (조각 한정)** |
| 저장소 전체 Python `compileall` | 저장소 전체 소스가 로컬에 없고 GitHub 커넥터만 사용 | **NOT_RUN** |
| 신규/전체 `pytest` | 현 컨테이너에 `mujoco`, `gymnasium`, `stable_baselines3` 미설치 | **NOT_RUN** |
| MuJoCo / PPO / ROS 2 / Gazebo 실기동 | 호환 실행 환경 부재 | **NOT_RUN** |

**주의:** 기존 `Ch12/evidence/`의 2026-10-17 PASS 값은 과거 커밋에서 얻은 실행 기록이다. 이번 변경의 PASS나 학습·실기 성능으로 재인용하지 않는다. `PATCH_FRAGMENT_SYNTAX_PASS`는 원격 전체 파일 컴파일 성공을 뜻하지 않는다. 새로운 pytest 함수도 **추가했을 뿐 이 세션에서 실행하지 않았다**.

## 4. 검증 재현 명령

저장소 루트, 대상 브랜치를 checkout한 깨끗한 Python 3.12 환경에서 수행한다. 앞 장 ROS overlay가 섞이지 않도록 한다.

```bash
git fetch origin docs/ch12-section-12-6-review-20261021
git switch docs/ch12-section-12-6-review-20261021
python -m compileall -q Ch12/src/quadruped_rl/avoidance_env.py Ch12/tests/test_avoidance_env.py
python -m pip install -e './Ch12[train,test]'
python -m pytest Ch12/tests/test_avoidance_env.py -q
# 실습 환경을 갖춘 다음 각 절의 LAB_12_6_GUIDE_KO.md를 따라 런타임 재검증
```

**미검증 후속 Acceptance:** `compileall` 종료 코드 0, 신규 pytest 및 관련 기존 회귀 PASS, 표준 시드의 reset/step와 기존 Policy Contract 불변, 필요시 12.8 ROS dry-run 및 물리 백엔드 재실행. 로그·Python 패키지 버전·seed·브랜치 HEAD SHA를 별도 증거로 보존한다. 실패를 재현하면 원인 및 최소 수정·재검증을 새 커밋에 남긴다.

## 5. 원고·다른 절과의 연결

이 수정은 원고에 기재된 관측/행동 차원, 물리 제어 주기, 정책 성능 수치를 근거 없이 바꾸지 않는다. 도서에는 **왜 입력 경계·오류 검출·시계 순서가 학습 및 ROS 제어 안전성과 연결되는지**를 설명하고, GitHub 가이드에는 완전한 실행 절차를 유지한다.

- 기준 기존 리뷰: [SECTION_12_6_REPORT_KO.md](SECTION_12_6_REPORT_KO.md)
- 독자 실습: [LAB_12_6_GUIDE_KO.md](LAB_12_6_GUIDE_KO.md)
- 절별 PR: https://github.com/silverbjin/Pysical_AI_ROS2/pull/109
