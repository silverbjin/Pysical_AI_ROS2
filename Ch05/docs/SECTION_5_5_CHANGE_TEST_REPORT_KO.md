# SECTION 5.5 — 수정 및 정적 테스트 보고서

- 브랜치: `docs/ch05-section-5-5-review-lab` / 이전 리뷰: `SECTION_5_5_REPORT_KO.md`
- ROS 2 Jazzy + RViz2/Gazebo Harmonic 대상. GUI와 TF 런타임은 NOT_RUN.

## 코드 변경
1. `rviz/manipulation.rviz` Fixed Frame을 기존 `base_link`에서 모델에 실제 존재하는 고정 `world`로 변경. 관절 상대 자세뿐 아니라 고정 월드 기준 표시의 목적을 명시.
2. 별도 `launch/rviz_only.launch.py` 추가: 기존 ROS graph가 실행 중일 때 `/robot_description`, `/joint_states`를 표시하는 RViz만 독립적으로 실행할 수 있게 분리.
3. `use_sim_time`은 launch 인자로 제공(기본 true), `ParameterValue(...,value_type=bool)`로 변환. 기존 통합 launch의 RViz 실행은 유지.
4. `RobotModel`은 `/robot_description`, TF display는 기존 사용 설정 유지.

## 정적 검사
| 분류 | 검사 | 상태 |
|---|---|---|
| SYNTAX | 추가 launch Python AST/compile | PASS |
| STATIC | RViz YAML 파싱, world/RobotModel/TF/Topic 계약 | PASS |
| STATIC | GitHub 원격 파일에 Fixed Frame, Description Topic, TF 존재 확인 | PASS |
| RUNTIME | RViz 실제 모델 로드, TF 누락·시간 동기화 | NOT_RUN |

로컬에서 launch+축약 RViz 계약 fixture 테스트: `python -m pytest test_5_5_static.py -q` → **2 passed**. 전체 원격 rviz 파일에 대한 최종 파싱/동작은 사용자 ROS 환경에서 재검증 필요. 저장소 명령: `python3 -m pytest Ch05/ros2_ws/src/manipulation_basics/test/test_section_5_5_static.py -q`.

## 사용 조건
통합 launch는 이미 RViz를 띄우므로 **동일한 ROS 그래프에서 중복 실행하지 말 것**. 분리 진단에서만 `ros2 launch manipulation_basics rviz_only.launch.py`. 현재 모델은 fixed world-to-base이므로 Gazebo 물리 베이스 움직임을 RViz가 자동 복제하는 것은 아니다.

**판정: SYNTAX / STATIC PASS, GUI·TF RUNTIME NOT_RUN.**
