# 11.4 코드 수정·정적 검증 보고서 (2026-10-21)

## 0. 기준과 권한
- 분기: `docs/ch11-section-11-4` / 변경 전 HEAD `d69293f3b39e4fadf145d77b03ae7b637aae2b77` / 기존 PR에 갱신
- 기준 리뷰: `Ch11/docs/SECTION_11_4_REPORT_KO.md`
- 코드: `Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/localization/lab_math.py`
- 검사: `Ch11/tests/test_ekf_lab.py`

## 1. 확인된 문제
교육용 /ekf_lab/raw의 명령 적분 모델에서 부동소수·역행 stamp_ns를 받아 오래된 /cmd_vel이 더 최신 명령을 덮어쓸 가능성이 있었다.

## 2. 수정·영향 범위
명령 시각의 정수·비음수 계약을 명시적으로 검사하고 역순 도착 명령을 예외로 거부한다. 이전 명령 상태 유지, EKF yaml/TF/출력 토픽과 교육용 scale/noise 계약 유지.

## 3. 테스트 기록
| 검증 단계 | 실제 수행 및 결과 |
|---|---|
| 변경 위치 고유성 확인 | 실제 브랜치 소스/테스트를 원격에서 읽어 대상 문자열이 각각 정확히 한 곳인지 확인: **STATIC_CHECK_PASS** |
| 수정 후 구조 검사 | 함수 선언, 회귀 test 메서드 및 변경 유무 비교: **STATIC_CHECK_PASS** |
| 회귀 커버리지 | out-of-order command rejection; noninteger stamp rejection; command state unchanged after invalid input — 테스트 추가, Python 실행은 **NOT_RUN** |
| `python3 -m py_compile`/`unittest` | **NOT_RUN** (사용자 ROS/WSL2 작업 공간에 로컬 checkout 없음) |
| `colcon build`, Gazebo, TF·Map runtime, E2E | **NOT_RUN** |

과거 `Ch11/evidence`의 기록은 기존 실험 증거일 뿐, 이번 커밋의 테스트 PASS로 계산하지 않는다. STATIC_CHECK_PASS는 GitHub 소스에 대한 결정적 패치·구조 검증이다.

## 4. 재실행 명령 (저장소 루트)
```bash
python3 -m py_compile Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/localization/lab_math.py Ch11/tests/test_ekf_lab.py
python3 -m unittest discover -s Ch11/tests -p 'test_ekf_lab.py' -v
```

## 5. 안전·출판 판정
- 운영 EKF 입력은 Gazebo 관측이며, 이 교육용 적분은 관절·발 접촉 오도메트리가 아니다.
- Python/ROS 실제 구동 전 출판 성공 또는 물리적 안전을 주장하지 않음.
