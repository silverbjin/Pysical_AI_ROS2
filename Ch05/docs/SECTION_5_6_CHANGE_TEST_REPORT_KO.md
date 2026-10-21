# SECTION 5.6 — 수정 및 정적 테스트 보고서

- 브랜치: `docs/ch05-section-5-6-review-lab`; 리뷰: `SECTION_5_6_REPORT_KO.md`
- ROS 2 Jazzy / Gazebo Harmonic 목표 환경, GUI 및 물리 운동 검증 NOT_RUN.

## 수정 내역
1. `wave_profile.py`: ROS 없이 단위 테스트 가능한 파형 위치·속도 생성기 분리. 관절1 진폭 0.22rad·각주파수 0.8rad/s, 관절4 진폭 0.28rad·각주파수 2.0rad/s. 이론 최대 속도 각각 0.176/0.56rad/s로 모델의 속도 한도보다 작음.
2. `wave_hello_node.py`: `use_sim_time` 미설정 시 구동 거부. /clock 유효성·subscriber·최신 JointState 확인 후 목표 발행.
3. 최초 한 번 3초짜리 준비 자세를 명령하고, 4관절 모두 오차 0.1rad 이내일 때만 WAVING으로 전이(6초 내 실패 시 중단).
4. JointState 0.5초 이상 오래됨 또는 시계 역행 시 후속 파형 명령 중단.
5. 20Hz 발행, 0.15초 look-ahead, 위치·속도 지정된 단일 포인트 trajectory 사용. 종료 시 마지막 목표를 유지할 수 있으므로 물리적 E-stop을 대신하지 않음.
6. `launch/wave_hello.launch.py`를 추가하여 `use_sim_time=True`로 독립 실행 경로 제공. 기존 `setup.py`의 wave_hello 엔트리포인트 유지.

## 정적 검증
| 분류 | 사례 | 결과 |
|---|---|---|
| SYNTAX | 세 Python 파일 AST/compile | PASS |
| UNIT | 501개 표본의 관절각·속도 상계 | PASS |
| UNIT | 준비 자세 검증(정상/누락/NaN/오차) | PASS |
| UNIT | 잘못된 시간 입력 4개 거부 | PASS |
| STATIC | sim_time·feedback stale·subscriber 확인 | PASS |
| BUILD/RUNTIME | Gazebo 관절 추종, 지터, 시뮬레이션 reset 후 안전성 | NOT_RUN |

로컬: `python -m pytest test_5_6_static.py -q` → **8 passed**. 원격 재현: `python3 -m pytest Ch05/ros2_ws/src/manipulation_basics/test/test_section_5_6_static.py -q`.

## 실습 실행 전제와 남은 검증
- 통합 Gazebo launch 실행 후 다른 명령 publisher(`simple_controller`)를 종료하고 `ros2 launch manipulation_basics wave_hello.launch.py` 사용.
- 정적 안전 가드는 실물 토크·충돌·구동 한계를 보장하지 않음. 포즈 이행 중 플러그인·제어기 상태, RViz/TF 동기화, 역행 시뮬레이션 시계, Ctrl+C와 마지막 명령 동작 실측 필요.
- 장간/절간 별도 브랜치 코드가 main에 아직 병합되지 않았을 수 있으므로 합친 뒤 회귀 테스트 필요.
- **판정: SYNTAX·UNIT STATIC PASS / BUILD·GAZEBO RUNTIME NOT_RUN.**
