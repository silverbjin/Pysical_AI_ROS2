# 11.1 코드 수정·정적 검증 보고서 (2026-10-21)

## 0. 기준과 범위
- 기존 브랜치: `docs/ch11-section-11-1` (변경 전 HEAD `9a653e86a31a32d785bf38912d841289dacef5ac`)
- 원고·리뷰 근거: `Ch11/docs/SECTION_11_1_REPORT_KO.md`, `LAB_11_1_GUIDE_KO.md`
- 수정 코드: `Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/command_odometry_demo.py`
- 회귀 검사: `Ch11/tests/test_section_11_1_patch.py`
- 사용자 요청에 따라 기존 절 브랜치에만 반영; main/다른 절 변경 없음.

## 1. 문제와 수정 근거
11.1 명령 적분 데모에서 NaN/Inf Twist가 odom 위치까지 전파될 수 있고, ROS clock 역행 또는 장시간 타이머 지연에서 음수/과대 dt를 적분할 수 있었다.

## 2. 최소 수정 내용
비정상 속도 명령을 즉시 0으로 거부하고, clock 역행 시 데모 포즈·속도를 초기화한다. 0.2초 초과 샘플 간격은 적분하지 않는다. /demo 토픽 및 운영 /odom 경로는 유지.

## 3. 정적 검사 및 실행 범위
| 항목 | 방법 | 결과 |
|---|---|---|
| 변경 소스 일치 | 기준 브랜치 파일 수신 후 단일 대상 위치 정확히 매칭하여 치환 | **STATIC_CHECK_PASS** |
| 변경 코드·회귀 파일 구조 | 함수 선언·회귀 코드 존재·텍스트 인코딩 및 패치 결과 검증 | **STATIC_CHECK_PASS** |
| 회귀 검사 대상 | nonfinite command rejection; finite 0.9-scale continuity; negative / excessive dt guards | **테스트 케이스 작성/수정, 실행 NOT_RUN** |
| Python `py_compile`, `unittest` | 대상 머신에서 직접 실행 필요 | **NOT_RUN** |
| ROS 2 Jazzy `colcon build` | WSL2/Jazzy 환경 필요 | **NOT_RUN** |
| Gazebo/Harmonic E2E, 물리 검증 | 실제 시뮬레이터/센서 스트림 필요 | **NOT_RUN** |

> 구분: STATIC_CHECK_PASS는 GitHub로부터 가져온 원본 소스에 대해 수행한 결정적 패치 위치·구조 검사의 결과이며, Python 단위 테스트를 실행한 결과가 아닙니다. 과거 `Ch11/evidence`의 PASS를 이번 실행으로 간주하지 않습니다.

## 4. 로컬 재검증 명령 (저장소 루트)
```bash
python3 -m py_compile Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/command_odometry_demo.py Ch11/tests/test_section_11_1_patch.py
python3 -m unittest discover -s Ch11/tests -p 'test_section_11_1_patch.py' -v
```

## 5. 교재/안전 판정 및 미완료
- 새 ROS2/Gazebo 테스트는 NOT_RUN; 데모는 물리적인 다리 오도메트리가 아님.
- 새 런타임 Evidence 없음. 출판 또는 물리적 안전 성공은 이 커밋만으로 주장할 수 없음.
- 11.1 기존 문서 PR에서 코드·정적 검사·실행 미검증의 경계를 유지해야 함.

## 6. 추가 오프라인 Python 검증 — 원격 반영 이후 수행
- 대상 코드 Git blob SHA: `e866f0bd0f5b8c9b23f721aeb0a7fa267ef0ee32`.
- 소스 동일성/검사 방법: 원격 원문 변경 콜백과 동등한 독립 코드 조각을 Python으로 컴파일/실행(전체 파일 바이트 일치 미검증).
- Python 문법: **핵심 수정 구문 AST_PASS; 전체 원격 소스 py_compile NOT_RUN**.
- 오프라인 회귀 smoke: **1/1 PASS** — NaN/Inf 명령 즉시 차단 및 정상 0.9 배율 동작.
- 실행 환경: 로컬 Python 3 (ROS 2/Gazebo 미설치), `unittest` 기반 독립 최소 회귀 시나리오. 실행 결과에서 FAIL/ERROR 없음.
- **주의:** 이 검사는 기존 `Ch11/tests/test_*.py` 전체를 직접 실행한 것이 아니므로 해당 종합 테스트는 **NOT_RUN**. ROS 2 colcon build·시뮬레이션·TF·맵 품질·태스크 성공은 **NOT_RUN**.
- 이 추가 기록은 앞의 초기 패치 시점 `NOT_RUN` 이후 수행된 **별도의 제한된 Python 검증**이며, 오프라인 단위 동작 범위를 넘는 성공을 증명하지 않는다.
