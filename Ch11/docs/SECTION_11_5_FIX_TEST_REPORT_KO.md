# 11.5 코드 수정·정적 검증 보고서 (2026-10-21)

## 0. 기준과 권한
- 분기: `docs/ch11-section-11-5` / 변경 전 HEAD `ffe8621e3710fb671c9763873f7cab184d4b20fe` / 기존 PR에 갱신
- 기준 리뷰: `Ch11/docs/SECTION_11_5_REPORT_KO.md`
- 코드: `Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/sensors/scan_gate.py`
- 검사: `Ch11/tests/test_slam_mapping.py`

## 1. 확인된 문제
SLAM 스캔 게이트에서 stamp_ns/now_ns의 비정수·NaN 입력 또는 orientation=None이 들어오면 비교·len 처리에서 예외가 발생하여 필터 노드의 콜백을 중단시킬 수 있었다.

## 2. 수정·영향 범위
입력 시각의 정수·양수 계약을 상태 변경 전에 검사하고 orientation=None을 명시적으로 'orientation'으로 거부한다. 정상 시각의 rate/tilt 게이트와 /scan/slam 출력 계약은 보존.

## 3. 테스트 기록
| 검증 단계 | 실제 수행 및 결과 |
|---|---|
| 변경 위치 고유성 확인 | 실제 브랜치 소스/테스트를 원격에서 읽어 대상 문자열이 각각 정확히 한 곳인지 확인: **STATIC_CHECK_PASS** |
| 수정 후 구조 검사 | 함수 선언, 회귀 test 메서드 및 변경 유무 비교: **STATIC_CHECK_PASS** |
| 회귀 커버리지 | invalid nan/float/None timestamp rejected; invalid timestamp leaves throttle state unchanged; missing quaternion rejected — 테스트 추가, Python 실행은 **NOT_RUN** |
| `python3 -m py_compile`/`unittest` | **NOT_RUN** (사용자 ROS/WSL2 작업 공간에 로컬 checkout 없음) |
| `colcon build`, Gazebo, TF·Map runtime, E2E | **NOT_RUN** |

과거 `Ch11/evidence`의 기록은 기존 실험 증거일 뿐, 이번 커밋의 테스트 PASS로 계산하지 않는다. STATIC_CHECK_PASS는 GitHub 소스에 대한 결정적 패치·구조 검증이다.

## 4. 재실행 명령 (저장소 루트)
```bash
python3 -m py_compile Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/sensors/scan_gate.py Ch11/tests/test_slam_mapping.py
python3 -m unittest discover -s Ch11/tests -p 'test_slam_mapping.py' -v
```

## 5. 안전·출판 판정
- SLAM lifecycle/지도 저장의 실제 성공은 별도 런타임 확인이 필요하다.
- Python/ROS 실제 구동 전 출판 성공 또는 물리적 안전을 주장하지 않음.

## 6. 추가 오프라인 Python 검증 — 원격 반영 이후 수행
- 대상 코드 Git blob SHA: `58f91fb099d5bd0a59e84093d8f51e8dac3dc3d5`.
- 소스 동일성/검사 방법: SHA 일치 scan_gate.py 직접 import / unittest.
- Python 문법: **원본 전체 py_compile PASS**.
- 오프라인 회귀 smoke: **3/3 PASS** — 불량 시각 불변조건, orientation=None 차단, 기울기 게이트.
- 실행 환경: 로컬 Python 3 (ROS 2/Gazebo 미설치), `unittest` 기반 독립 최소 회귀 시나리오. 실행 결과에서 FAIL/ERROR 없음.
- **주의:** 이 검사는 기존 `Ch11/tests/test_*.py` 전체를 직접 실행한 것이 아니므로 해당 종합 테스트는 **NOT_RUN**. ROS 2 colcon build·시뮬레이션·TF·맵 품질·태스크 성공은 **NOT_RUN**.
- 이 추가 기록은 앞의 초기 패치 시점 `NOT_RUN` 이후 수행된 **별도의 제한된 Python 검증**이며, 오프라인 단위 동작 범위를 넘는 성공을 증명하지 않는다.
