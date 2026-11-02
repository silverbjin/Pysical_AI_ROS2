# 9.3절 코드 리뷰 — 관성 텐서·질량 중심·충돌 형상

검토일: 2026-10-21 (KST) · 기준 main: `bab76f6ca7df` · 원고: 「9.3 시뮬레이션의 핵심: 관성과 충돌 속성」

**결론: 소스 정적 리뷰 완료 / ROS 2·Gazebo 실제 실행 NOT_RUN / 전체 실습 성공 미인증.**
이번 PR은 요청에 따라 Markdown 보고서와 따라하기 가이드만 추가하며 소스 코드는 변경하지 않는다.

## 리뷰 대상

- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/common/inertial_macros.xacro`
- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/parts/leg.xacro`
- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/robot.urdf.xacro`
- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/common/robot_properties.xacro`

## 발견 사항 및 개선 제안

| No. | 우선순위 | 근거: 원본 소스 상태 | 개선 및 확인 지점 |
|---|---|---|---|
| 1 | 확인 | box/cylinder/sphere 관성 매크로는 균일 질량 도형의 기본 모멘트 공식을 사용 | 수식 패턴은 타당. 실제 확장된 텐서/좌표 방향을 확인해야 함 |
| 2 | 높음 | thigh, calf는 collision 중심 z=-0.125 m인데 inertial 중심 z=-0.05 m | 각 0.075m 차이가 실제 질량분포 의도인지 확인. 별도 질량 집중 모델 근거 없다면 정렬 권고 |
| 3 | 주의 | 원고 9.3.3은 원통 관성 매크로의 xyz/rpy 필수 호출 예시가 섞여 있으나 실제 코드에는 기본값이 있음 | 독자가 복사할 코드 대신 repo의 최신 매크로 정의를 기준으로 기술 |
| 4 | 주의 | foot collision은 sphere 반지름 0.02m, foot 질량 0.1kg; 다리당 foot fixed joint | 단순 접촉 모델 적합성은 정적 형상 검사 외 Gazebo에서 실제 접촉 안정성 확인 필요 |
| 5 | 주의 | 인접 관절 collision의 실제 중첩, 고속 컨트롤러의 안정성은 URDF 문자열만으로 판정 불가 | Gazebo GUI/물리 로그와 질량·관성 범위 기록 |

## 검증과 한계

- **실시:** GitHub main의 실제 파일을 읽어 Xacro 구성, launch·Python 연계 및 첨부 원고의 9.3절 설명을 정적으로 대조했다. 사용한 분석 대상이 코드 수정 PR의 상태가 아니라 **위 main 기준 SHA**임을 유의한다.
- **미실시(NOT_RUN):** `xacro` CLI 전개, `check_urdf`, `rosdep`, `colcon build/test`, Gazebo Harmonic 물리 계산과 WSLg/RViz 실행, 실제 ROS 토픽 검증. 네이티브 ROS/Gazebo 실행 환경이 이 세션에 없으므로 PASS를 주장하지 않는다.
- **확정 실패(FAIL)와 구별:** 정적으로 확인된 논리 문제는 표에 기록했다. 아직 실행하지 않은 항목을 실패 또는 성공으로 꾸미지 않는다.

## 재현 및 수용 기준

1. 전개된 URDF 전체 질량은 몇 kg인가?
2. thigh와 calf의 충돌 중심과 관성 중심은 각각 얼마만큼 다른가?
3. 관성 매크로의 축과 원통의 길이축은 일치하는가?
4. 자유낙하 후 로봇이 지면에 안착하는가(물리 실행 환경에서만 판정)?

**판정:** 형상별 inertia가 양수이고 합계 12.0kg이며, 중심 좌표 차이를 설명할 수 있어야 한다. 안정성은 실제 Gazebo 재현으로만 판정한다.

## 원고 정합성·후속 조치

원고의 '물리적으로 완벽하다'는 설명은 실제 코드의 질량중심·충돌중심 불일치와 검증 부재를 고려하면 과한 단정이다.

각 항목 수정이 필요한 경우 별도 코드 수정 브랜치에서 RED→GREEN 회귀 검증, 실행 로그 및 소스 차이를 남길 것을 권장한다. [9.3 실습 가이드](LAB_9_3_GUIDE_KO.md), [대상 코드](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09).
