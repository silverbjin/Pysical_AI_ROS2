# 11.3 코드 수정·정적 검증 보고서 (2026-10-21)

## 0. 기준과 범위
- 기존 브랜치: `docs/ch11-section-11-3` (변경 전 HEAD `44da3734423b53041f79d3d853bb06e832b0bac5`)
- 원고·리뷰 근거: `Ch11/docs/SECTION_11_3_REPORT_KO.md`, `LAB_11_3_GUIDE_KO.md`
- 수정 코드: `Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/sensors/lidar_processing.py`
- 회귀 검사: `Ch11/tests/test_lidar_processing.py`
- 사용자 요청에 따라 기존 절 브랜치에만 반영; main/다른 절 변경 없음.

## 1. 문제와 수정 근거
11.3 전방 LiDAR 측정치가 safe_distance와 정확히 같은 경우 기존 `<` 조건으로 CLEAR 판정되었다. 교재의 경고 거리 경계와 안전 측면에서 경계값을 일관되게 다룰 필요가 있다.

## 2. 최소 수정 내용
경고 임계값을 <= 로 판정하도록 수정, 기존 strict-less-than 단위 테스트를 포괄 경계값 회귀 테스트로 업데이트. UNKNOWN/STALE 처리는 유지하고 /cmd_vel 자동 제동 기능은 추가하지 않는다.

## 3. 정적 검사 및 실행 범위
| 항목 | 방법 | 결과 |
|---|---|---|
| 변경 소스 일치 | 기준 브랜치 파일 수신 후 단일 대상 위치 정확히 매칭하여 치환 | **STATIC_CHECK_PASS** |
| 변경 코드·회귀 파일 구조 | 함수 선언·회귀 코드 존재·텍스트 인코딩 및 패치 결과 검증 | **STATIC_CHECK_PASS** |
| 회귀 검사 대상 | 0.49/0.50 m OBSTACLE; 0.51 m CLEAR; non-finite remains UNKNOWN | **테스트 케이스 작성/수정, 실행 NOT_RUN** |
| Python `py_compile`, `unittest` | 대상 머신에서 직접 실행 필요 | **NOT_RUN** |
| ROS 2 Jazzy `colcon build` | WSL2/Jazzy 환경 필요 | **NOT_RUN** |
| Gazebo/Harmonic E2E, 물리 검증 | 실제 시뮬레이터/센서 스트림 필요 | **NOT_RUN** |

> 구분: STATIC_CHECK_PASS는 GitHub로부터 가져온 원본 소스에 대해 수행한 결정적 패치 위치·구조 검사의 결과이며, Python 단위 테스트를 실행한 결과가 아닙니다. 과거 `Ch11/evidence`의 PASS를 이번 실행으로 간주하지 않습니다.

## 4. 로컬 재검증 명령 (저장소 루트)
```bash
python3 -m py_compile Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/sensors/lidar_processing.py Ch11/tests/test_lidar_processing.py
python3 -m unittest discover -s Ch11/tests -p 'test_lidar_processing.py' -v
```

## 5. 교재/안전 판정 및 미완료
- 경계 포괄은 교육용 경고의 보수적 기준이며 하드웨어 인증 AEB 아님.
- 새 런타임 Evidence 없음. 출판 또는 물리적 안전 성공은 이 커밋만으로 주장할 수 없음.
- 11.3 기존 문서 PR에서 코드·정적 검사·실행 미검증의 경계를 유지해야 함.
