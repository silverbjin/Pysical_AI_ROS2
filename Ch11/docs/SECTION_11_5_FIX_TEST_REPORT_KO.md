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
