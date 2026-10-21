# 11.7 코드 수정·정적 검증 보고서 (2026-10-21)

## 0. 근거 및 범위
- 기준: `docs/ch11-section-11-7` 변경 전 HEAD `1b805c6f9c049a3c1824c19999eeab29b68e53d2`, `SECTION_11_7_REPORT_KO.md`
- 변경: `Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/mission/map_artifacts.py`, `Ch11/tests/test_autonomous_mapping.py`

## 1. 실제 결함과 수정
`read_pgm`이 P5 파일에 width*height보다 큰 페이로드가 들어 있어도 앞의 픽셀만 잘라 정상으로 인정했다. 파일 헤더와 데이터 길이가 다른 손상된 PGM을 정상 지도로 오인하지 않도록 **추가 래스터 바이트를 ValueError로 거부**한다. 기존 정상·절단된 파일 처리는 유지한다.

## 2. 이번 실행의 검증 상태
| 항목 | 상태 및 범위 |
|---|---|
| 소스/테스트에 대한 일치 패턴 단일 치환, 보존 구조 확인 | **STATIC_CHECK_PASS** |
| 정확한 P5 바이트열 회귀 검사 추가 여부 확인 | **STATIC_CHECK_PASS** |
| `python3 -m py_compile`, `unittest` | **NOT_RUN** — 원격 GitHub 파일로 수정/정적 대조만 실시 |
| Jazzy colcon build/Gazebo/자동 저장 시뮬레이션 | **NOT_RUN** |

STATIC_CHECK_PASS는 Python 런타임 PASS나 물리·지도 품질 PASS가 아니다. 기존 `Ch11/evidence/autonomous_mapping_validation.json` 기록도 이번 실행으로 재계산하지 않는다.

## 3. 로컬 회귀 검사 명령 (저장소 루트)
```bash
python3 -m py_compile Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/mission/map_artifacts.py Ch11/tests/test_autonomous_mapping.py
python3 -m unittest discover -s Ch11/tests -p test_autonomous_mapping.py -v
```

## 4. 한계
헤더/래스터 크기의 일치가 지도 전체 탐사·맵 지오메트리 정확성·로봇 자율주행 태스크 성공을 보증하지 않는다. 실제 지도 저장은 WSL2/Gazebo의 별도 Evidence 확보 필요.

## 6. 추가 오프라인 Python 검증 — 원격 반영 이후 수행
- 대상 코드 Git blob SHA: `276d052964ad9a59b63bae660d8857c6f2c9da21`.
- 소스 동일성/검사 방법: SHA 일치 map_artifacts.py 직접 import / unittest.
- Python 문법: **원본 전체 py_compile PASS**.
- 오프라인 회귀 smoke: **3/3 PASS** — PGM 래스터 과잉·정상·잘림 데이터 판정.
- 실행 환경: 로컬 Python 3 (ROS 2/Gazebo 미설치), `unittest` 기반 독립 최소 회귀 시나리오. 실행 결과에서 FAIL/ERROR 없음.
- **주의:** 이 검사는 기존 `Ch11/tests/test_*.py` 전체를 직접 실행한 것이 아니므로 해당 종합 테스트는 **NOT_RUN**. ROS 2 colcon build·시뮬레이션·TF·맵 품질·태스크 성공은 **NOT_RUN**.
- 이 추가 기록은 앞의 초기 패치 시점 `NOT_RUN` 이후 수행된 **별도의 제한된 Python 검증**이며, 오프라인 단위 동작 범위를 넘는 성공을 증명하지 않는다.
