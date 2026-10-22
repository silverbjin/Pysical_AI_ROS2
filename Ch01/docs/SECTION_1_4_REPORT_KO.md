# SECTION 1.4 — 원고·코드 리뷰: 워크스페이스의 구조와 이해

- 작성: 2026-10-20 KST
- 기준: silverbjin/Pysical_AI_ROS2 / main f5aed1d250563efc298e717559497db3b4f205c7
- 브랜치: feat/ch01-section-1-4
- 범위: 원고 1.4.1~1.4.3. 저장소 Ch01/robot_ws/src/examples 및 examples_rclpy_minimal_publisher; workspace 구조와 underlay/overlay 검증.
- 판정: **MANUSCRIPT_REVIEWED / STATIC_CODE_REVIEWED / ROS_RUNTIME_NOT_RUN**

## 1. 원고·저장소 대응

실제 Ch01의 공식 예제 경로와 `package.xml`을 열어 `examples_rclpy_minimal_publisher` 패키지 및 `publisher_member_function` entry point를 확인했다. Ch01 루트는 워크스페이스 자체가 아니며 `robot_ws/src/examples` 트리에 여러 개의 패키지가 들어 있다.

## 2. 리뷰 결과와 수정 우선순위

| ID | 중요도 | 확인된 불일치·문제점 | 개선 방안 |
|---|---|---|---|
| C01-14-01 | High | 원고 `source ~/robot_ws/install/setup.`는 실제 존재하지 않는 파일명 | `source ~/robot_ws/install/setup.bash`로 반드시 교정 |
| C01-14-02 | Medium | `git clone ros2/examples` 전체 → `rosdep install` 전체 → `colcon build` 전체를 초심자 필수로 제시 | Ch01에 포함된 예제 중 `examples_rclpy_minimal_publisher`만 고립 복사해 선택 빌드; 전체 빌드는 선택 과제 |
| C01-14-03 | Medium | Ch01/robot_ws/src/examples 하위는 대규모 공식 ROS2 예제 트리 | 학습에 필요한 최소 패키지만 선정하고 중첩 clone 및 종속성 폭증 방지 |
| C01-14-04 | Medium | `--symlink-install`이면 Python 수정이 언제나 즉시 반영된다는 단정 | 노드 재시작은 필요, entry point/setup.py/package.xml 갱신 시 재빌드 필요 |
| C01-14-05 | High | `rm -rf build install log`는 경로 실수 시 데이터 삭제 위험 | `pwd`·작업 디렉터리·백업 확인 후 제한적으로만 사용 |
| C01-14-06 | Medium | 언더레이/오버레이 우선순위가 기존 장 install의 잔여 환경에 의해 바뀔 수 있음 | `ros2 pkg prefix`, `AMENT_PREFIX_PATH` 확인과 새 셸 절차 추가 |

## 3. 구현·테스트 기록

- 생성 문서: `Ch01/docs/SECTION_1_4_REPORT_KO.md`, `Ch01/docs/LAB_1_4_GUIDE_KO.md`.
- 이 브랜치는 현재 저장소를 덮어쓰지 않는 **원고 오류 교정, 검증 가능한 실습 명령 문서화**를 수행했다.
- **REVIEWED:** 실제 main 소스·패키지 메타데이터 및 원고 예제·명령어 비교.
- **NOT_RUN:** Python 소스 동작, ROS 2 Jazzy/colcon 빌드, publisher/graph 실측, CI 기능 테스트. 현재 환경에는 ros2/colcon이 없어 추정 PASS를 부여하지 않는다.
- `source install/setup.`, `--node_name`는 **원고에 있는 오류**로 가이드에서 정정했으며 원고 원문은 별도 수정하지 않았다.

## 4. 최종 검증·증거

[LAB_1_4_GUIDE_KO.md](LAB_1_4_GUIDE_KO.md)에 각 명령·기대 출력·ACCEPT 조건이 있다. Ubuntu 24.04/Jazzy에서 `git rev-parse HEAD`와 `ros2 doctor --report`, 전체 명령 로그·exit code를 보존한 다음에만 EXECUTION_ACCEPT 판단을 할 수 있다. Ch12의 과거 Gazebo/MuJoCo 테스트 실적을 Ch01에 인용해 통과 처리하지 않는다.

## 참고
- [Jazzy 공식 패키지 생성](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html)
- [Jazzy 공식 워크스페이스 생성](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html)
