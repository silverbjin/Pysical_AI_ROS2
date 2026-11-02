# 9.8절 코드 리뷰 — 통합 QA·트러블슈팅·다음 장 인계

- 검토일: **2026-10-21 (KST)** · 기준 main `bab76f6ca7df0bda6efd8882c1a698561707e51d`
- 원고: 9.8 「9.8 프로젝트 마무리 및 트러블 슈팅」
- 결론: **정적 검토 완료, ROS 2·Gazebo 런타임 NOT_RUN, 코드 실행 가능성 미인증**
- 범위: 요청된 리뷰/실습 문서만 추가하며 기존 소스는 수정하지 않음

## 검토한 실제 소스

- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/robot.urdf.xacro`
- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/parts/leg.xacro`
- `Ch09/ros2_ws/src/my_quadruped_bot/worlds/empty_world.sdf`
- `Ch09/ros2_ws/src/my_quadruped_bot/config/ros_gz_bridge.yaml`
- `Ch09/ros2_ws/src/my_quadruped_bot/launch/simulation.launch.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/launch/display.launch.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/stand_up.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/single_leg_mover.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/trot_gait_preview.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/package.xml`
- `Ch09/ros2_ws/src/my_quadruped_bot/setup.py`

## 발견 사항

| 심각도 | 실제 코드 관찰 | 문제·개선 권고 |
|---|---|---|
| 높음 | 9.1~9.7에 드러난 launch 경로·시간·동시제어 문제는 전체 통합 실습에 직접 영향 | 정적 리뷰 문제 목록을 단계적 회귀 체크리스트로 전환 |
| 확인 | 전개 기대 총질량은 base6 + 4*(hip0.2+thigh0.7+calf0.5+foot0.1)=12kg | 원고 10~15kg 기준에는 포함되나 원고 부품별 수치와 다름 |
| 주의 | leg.xacro의 inertia vs collision center 및 foot friction 값 적용 불명확 | SDF 변환과 실제 물리 장면에서 기록 필요 |
| 높음 | package.xml의 실제 의존성 선언 부족, RViz launch가 Ch08 패키지 이름 참조 | 새 머신에서 Ch09 독립 재현 실패 가능성. clean overlay 검증 필요 |
| 높음 | source install/setup. 는 원고 오타, 설치 패키지 중복 overlay 가능 | setup.bash로 정정하고 Ch09 pkg prefix를 확인 |
| 주의 | 프로젝트에 trot_gait_preview.py가 추가로 있으나 원고 9.8 QA에는 별도 기대/위험 항목 없음 | 보행 안정성과 제자리 다리 파형 미리보기를 구분 |

## 리뷰 절차와 실행 검증의 구분

- **정적 리뷰:** 원격 GitHub main의 파일 전문과 첨부 원고를 대조하여 명칭, 값, 토픽·의존성·실행 흐름의 논리 문제를 확인했다.
- **NOT_RUN:** 이 환경에는 실제 ROS 2 Jazzy / Gazebo Harmonic 시뮬레이터가 준비되어 있지 않다. `colcon build`, `colcon test`, GUI, 브리지 통신, 관절 동작·물리 기립, WSL2 화면을 실행하지 않았다.
- **검증 보류:** 원격에서 읽은 파일이 XML·Python 구문상 무오류임을 `xacro`나 ROS 런타임 결과로 확인한 것은 아니다. 아래 기대는 가이드에 있는 사용자의 실행 결과로 검증해야 한다.

## 검증 수용 기준 및 재현 지점

1. XML/YAML·Python 구문 검사 결과와 colcon test 결과를 각각 보존했는가?
2. 로봇 총질량·TF·브리지 12개가 실제로 확인되었는가?
3. Gazebo 20초 기립 중 자세 오차와 미끄러짐을 기록했는가?
4. Ch10으로 인계할 관절 영점·이름·부호·소유권 계약을 문서화했는가?

**통과 기준:** 정적 규칙과 실제 물리 성공을 독립 PASS/FAIL 판정하고 근거 로그를 확보해야 다음 장의 보행 코드에 연결한다. 현재 이 PR만으로 Ch09 전체 기능을 PASS 판정하지 않는다.

## 원고·교재 수정 및 후속 구현 권고

원고의 '마무리/기립 성공' 서술은 테스트 실제 증거 확보 후에만 승인할 수 있다. 현행 루트는 base_footprint이고, WSL2 오버레이 충돌도 재현성 위험이다.

실제 코드 변경은 별도 승인된 수정 작업에서 담당하도록 남긴다. 수정 후에 같은 명령으로 RED→GREEN, 빌드·runtime·Evidence를 남겨야 한다. [실습 가이드](LAB_9_8_GUIDE_KO.md) · [Ch09 원본](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09).
