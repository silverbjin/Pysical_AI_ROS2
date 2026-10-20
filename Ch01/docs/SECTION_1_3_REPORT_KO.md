# SECTION 1.3 — 원고·코드 리뷰: 노드·메시지·인터페이스

- 작성: 2026-10-20 KST
- 기준: silverbjin/Pysical_AI_ROS2 / main f5aed1d250563efc298e717559497db3b4f205c7
- 브랜치: feat/ch01-section-1-3
- 범위: 원고 1.3.1~1.3.5: Node, Lifecycle, msg/srv/action, Cafe Serving Robot 사례. Ch01에는 사용자 정의 .msg/.srv/.action 파일 없음.
- 판정: **MANUSCRIPT_REVIEWED / STATIC_REVIEWED / ROS_RUNTIME_NOT_RUN**

## 1. 원고·저장소 매핑

원고의 인터페이스 파일은 설명용 가상 스니펫이며 Ch01 저장소에는 생성 패키지가 없다. 따라서 Jazzy 기본 튜토리얼 turtlesim으로 topic/service/action API 사용을 관찰한다.

## 2. 결함/정정 사항

| ID | 중요도 | 관찰·오해 가능성 | 권고 조치 |
|---|---|---|---|
| C01-13-01 | High | 모든 ROS 노드가 Unconfigured/Inactive/Active/Finalized 생명주기를 자동 갖는 듯한 설명 | 일반 Node와 Managed Lifecycle Node를 구분 |
| C01-13-02 | Medium | 노드 이름이 기술적으로 반드시 유일해야 한다는 단정 | 중복 실행은 가능하나 CLI/서비스 충돌이 발생하므로 고유 이름을 권장 |
| C01-13-03 | Medium | 서비스는 항상 동기 블로킹이며 액션은 항상 취소된다는 단정 | 비동기 service call 가능, action cancel은 서버가 승인/처리해야 함 |
| C01-13-04 | High | 원고 인터페이스 .msg/.srv/.action을 실제 저장된 Ch01 코드로 오인 | 예시 텍스트임을 명시, rosidl 패키지 생성/빌드는 별도 과제 |
| C01-13-05 | Medium | 명령 발행=물리 로봇 안전 정지라는 오해 | 실물은 watchdog/E-stop/제어권/타임아웃 필요 |

## 3. 구현·검증 및 남은 작업

- 문서 생성: `Ch01/docs/SECTION_1_3_REPORT_KO.md`, `Ch01/docs/LAB_1_3_GUIDE_KO.md`.
- 이 절에 고유 패키지 소스가 없는 경우, **원고의 코드가 실제 구현된 것처럼 판정하지 않는다**. 실습은 Jazzy 기본 패키지 및 CLI로 구성했다.
- **REVIEWED:** 업로드 원고와 저장소 대응, 기존 코드 범위 및 절 번호, 공식 Jazzy 설치/CLI 흐름.
- **NOT_RUN:** ROS 2 Jazzy/colcon/DDS/turtlesim/Gazebo 실제 실행 및 성능 수치. 현재 작업 환경에는 ros2와 colcon이 없다.
- 수정된 파일·실제 실행 명령·결과 수치는 각 검증 장소에서 별도 기록해야 한다. Ch12의 성공 로그를 Ch01 결과로 전용하지 않는다.

## 4. 재현/Acceptance

[LAB_1_3_GUIDE_KO.md](LAB_1_3_GUIDE_KO.md)의 STEP, 기대 출력, 실패 판정 기준에 따라 Ubuntu 24.04/ROS 2 Jazzy에서 실측한다. `git rev-parse HEAD`, `ros2 doctor --report`, 원본 로그, PASS/FAIL/NOT_RUN을 함께 저장하고 이 보고서를 갱신한 후 실습 Acceptance를 승인한다.

## 참고
- [ROS 2 Jazzy 공식 문서](https://docs.ros.org/en/jazzy/)
- [Ubuntu Jazzy deb 설치](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
