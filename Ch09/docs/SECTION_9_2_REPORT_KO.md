# 9.2절 코드 리뷰 — Xacro 매크로와 4개 다리 자동 생성

검토일: 2026-10-21 (KST) · 기준 main: `bab76f6ca7df` · 원고: 「9.2 효율적인 모델링을 위한 Xacro 매크로 설계」

**결론: 소스 정적 리뷰 완료 / ROS 2·Gazebo 실제 실행 NOT_RUN / 전체 실습 성공 미인증.**
이번 PR은 요청에 따라 Markdown 보고서와 따라하기 가이드만 추가하며 소스 코드는 변경하지 않는다.

## 리뷰 대상

- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/robot.urdf.xacro`
- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/parts/leg.xacro`
- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/common/robot_properties.xacro`
- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/common/materials.xacro`
- `Ch09/ros2_ws/src/my_quadruped_bot/setup.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/launch/display.launch.py`

## 발견 사항 및 개선 제안

| No. | 우선순위 | 근거: 원본 소스 상태 | 개선 및 확인 지점 |
|---|---|---|---|
| 1 | 확인 | 메인 Xacro는 common 4개와 parts/leg.xacro를 include하고 FR/FL/RR/RL 매크로를 각각 1회 호출 | 동일 링크 정의를 복제하지 않는 재사용 구조는 적절 |
| 2 | 주의 | robot_properties.xacro의 hip_mass=0.20 / thigh_mass=0.70, 원고의 표는 hip=0.50 / thigh=1.00 | 책의 파라미터 표와 실제 코드를 통일하거나 변경 근거 명시 |
| 3 | 높음 | display.launch.py가 get_package_share_directory('my_robot_description')를 호출 | Ch09 단독 설치에서는 RViz launch가 실패할 수 있음. Ch09 패키지 이름으로 변경 권고 |
| 4 | 주의 | setup.py walk_and_collect()가 urdf/**/*.draft, *.1, *.2 등 초안 파일까지 설치 자산으로 수집 | 배포 패키지에서 미사용 초안 제외 또는 archive로 분리 권고 |
| 5 | 주의 | leg.xacro의 관절 origin rpy에 굽힘 회전(1.2, -2.4)이 하드코딩 | 로봇 nominal/zero pose와 별도로 설명하고 Ch10/Ch12 인터페이스 확인 |

## 검증과 한계

- **실시:** GitHub main의 실제 파일을 읽어 Xacro 구성, launch·Python 연계 및 첨부 원고의 9.2절 설명을 정적으로 대조했다. 사용한 분석 대상이 코드 수정 PR의 상태가 아니라 **위 main 기준 SHA**임을 유의한다.
- **미실시(NOT_RUN):** `xacro` CLI 전개, `check_urdf`, `rosdep`, `colcon build/test`, Gazebo Harmonic 물리 계산과 WSLg/RViz 실행, 실제 ROS 토픽 검증. 네이티브 ROS/Gazebo 실행 환경이 이 세션에 없으므로 PASS를 주장하지 않는다.
- **확정 실패(FAIL)와 구별:** 정적으로 확인된 논리 문제는 표에 기록했다. 아직 실행하지 않은 항목을 실패 또는 성공으로 꾸미지 않는다.

## 재현 및 수용 기준

1. 4개의 다리에 총 12개 유일한 회전 관절이 전개되는가?
2. robot_properties.xacro 한 곳의 변수 변경이 4개 다리에 모두 반영되는가?
3. Ch09 단독 overlay에서 display.launch.py가 작동하는가? 실패한다면 정확히 어떤 패키지 조회가 원인인가?

**판정:** Xacro 확장, 링크/조인트 고유성, 설치된 파일 위치가 확인되어야 한다. RViz 실행은 현재 교차 패키지 참조 문제를 분리해 판정한다.

## 원고 정합성·후속 조치

원고의 예시 `xacro ~/ros2_ws/src/my_bot/...`는 실제 Ch09 경로가 아니다. 실제 패키지 share 경로를 사용한다.

각 항목 수정이 필요한 경우 별도 코드 수정 브랜치에서 RED→GREEN 회귀 검증, 실행 로그 및 소스 차이를 남길 것을 권장한다. [9.2 실습 가이드](LAB_9_2_GUIDE_KO.md), [대상 코드](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09).
