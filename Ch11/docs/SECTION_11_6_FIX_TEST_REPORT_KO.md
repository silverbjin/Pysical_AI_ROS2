# 11.6 코드 수정·정적 검증 보고서 (2026-10-21)

## 0. 기준과 권한
- 분기: `docs/ch11-section-11-6` / 변경 전 HEAD `2d313d759ddec8832f0878a667ee9988d56b1c86` / 기존 PR에 갱신
- 기준 리뷰: `Ch11/docs/SECTION_11_6_REPORT_KO.md`
- 코드: `Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/sensors/attitude_history.py`
- 검사: `Ch11/tests/test_slam_optimization.py`

## 1. 확인된 문제
센서 히스토리가 이전 시각보다 아주 조금 늦게 도착한 IMU 패킷에도 전체 deque를 초기화하여 /scan_stabilized 유효 표본이 일시 중단되는 문제가 있었다.

## 2. 수정·영향 범위
max_delta_ns 이내의 소규모 역순 메시지는 폐기하고 기존 히스토리를 보존한다. 큰 clock rewind는 기존처럼 초기화하며 실제 시각에 가장 근접한 유효성 판정을 유지한다.

## 3. 테스트 기록
| 검증 단계 | 실제 수행 및 결과 |
|---|---|
| 변경 위치 고유성 확인 | 실제 브랜치 소스/테스트를 원격에서 읽어 대상 문자열이 각각 정확히 한 곳인지 확인: **STATIC_CHECK_PASS** |
| 수정 후 구조 검사 | 함수 선언, 회귀 test 메서드 및 변경 유무 비교: **STATIC_CHECK_PASS** |
| 회귀 커버리지 | small out-of-order packet preserves history; large clock rewind clears history; unavailable orientation is not assumed level — 테스트 추가, Python 실행은 **NOT_RUN** |
| `python3 -m py_compile`/`unittest` | **NOT_RUN** (사용자 ROS/WSL2 작업 공간에 로컬 checkout 없음) |
| `colcon build`, Gazebo, TF·Map runtime, E2E | **NOT_RUN** |

과거 `Ch11/evidence`의 기록은 기존 실험 증거일 뿐, 이번 커밋의 테스트 PASS로 계산하지 않는다. STATIC_CHECK_PASS는 GitHub 소스에 대한 결정적 패치·구조 검증이다.

## 4. 재실행 명령 (저장소 루트)
```bash
python3 -m py_compile Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/sensors/attitude_history.py Ch11/tests/test_slam_optimization.py
python3 -m unittest discover -s Ch11/tests -p 'test_slam_optimization.py' -v
```

## 5. 안전·출판 판정
- 센서 재정렬 임계값은 max_delta이며 완전한 ROS clock epoch 판정기나 LiDAR deskew는 아니다.
- Python/ROS 실제 구동 전 출판 성공 또는 물리적 안전을 주장하지 않음.
