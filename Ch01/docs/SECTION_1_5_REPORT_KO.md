# SECTION 1.5 — 원고·코드 리뷰: colcon 빌드 시스템과 패키지 생성

- 작성: 2026-10-20 KST
- 기준: silverbjin/Pysical_AI_ROS2 / main f5aed1d250563efc298e717559497db3b4f205c7
- 브랜치: feat/ch01-section-1-5
- 범위: 원고 1.5.1~1.5.5; 저장소 Ch01/robot_ws/src/my_robot_controller/package.xml, setup.py/setup.cfg, 실제 entry point test_node.
- 판정: **MANUSCRIPT_REVIEWED / STATIC_CODE_REVIEWED / ROS_RUNTIME_NOT_RUN**

## 1. 원고·저장소 대응

원격 `my_robot_controller/setup.py`를 읽어 실제 `console_scripts=['test_node = my_robot_controller.simple_controller:main']`, `setup.cfg`와 `package.xml`이 존재함을 확인했다. 1.5절 원고는 패키지 생성 초기 상태, 1.6절은 노드 구현 완료 상태다.

## 2. 리뷰 결과와 수정 우선순위

| ID | 중요도 | 확인된 불일치·문제점 | 개선 방안 |
|---|---|---|---|
| C01-15-01 | High | `ros2 pkg create` 옵션이 원고에서 `--node_name`으로 표기됨 | Jazzy 공식 CLI는 `--node-name` (하이픈); 잘못된 명령은 옵션 인식 실패 |
| C01-15-02 | High | 원고 1.5.3 예시 `simple_controller` 실행파일과 기존 Ch01/setup.py의 `test_node`가 불일치 | 1.5절 새 생성 패키지 단계와 1.6절 최종 `test_node` 변경 단계를 구분 |
| C01-15-03 | High | 원고 `source install/setup.` 잘못된 확장자 | `source install/setup.bash`로 수정 |
| C01-15-04 | Medium | Jazzy ament_python 생성 패키지와 저장소에는 `setup.cfg`가 필수적인 실행 위치 설정 | `lib/my_robot_controller` 설치 경로 확인; 유무 검증 |
| C01-15-05 | Medium | `my_robot_controller`의 setup.py/manifest는 TODO 설명·라이선스 미확정 | 실습 실행에는 당장 차단은 아닐 수 있으나 배포·테스트 전 저작권자 검토 필요 |
| C01-15-06 | Low | 코드상 `std_msgs`를 import하지 않으나 package.xml 의존성 선언 | 학습 목적 선행 선언 가능; 실제 사용하지 않는 의존성은 후속 절에서 정리 |
| C01-15-07 | Medium | `--symlink-install`이 패키지 메타데이터 변경·entry point 변경에도 재빌드가 필요 없다고 오해 | 코드 저장 후 노드 재실행, entry point/패키지 의존성 변경 시 colcon 재빌드 |

## 3. 구현·테스트 기록

- 생성 문서: `Ch01/docs/SECTION_1_5_REPORT_KO.md`, `Ch01/docs/LAB_1_5_GUIDE_KO.md`.
- 이 브랜치는 현재 저장소를 덮어쓰지 않는 **원고 오류 교정, 검증 가능한 실습 명령 문서화**를 수행했다.
- **REVIEWED:** 실제 main 소스·패키지 메타데이터 및 원고 예제·명령어 비교.
- **NOT_RUN:** Python 소스 동작, ROS 2 Jazzy/colcon 빌드, publisher/graph 실측, CI 기능 테스트. 현재 환경에는 ros2/colcon이 없어 추정 PASS를 부여하지 않는다.
- `source install/setup.`, `--node_name`는 **원고에 있는 오류**로 가이드에서 정정했으며 원고 원문은 별도 수정하지 않았다.

## 4. 최종 검증·증거

[LAB_1_5_GUIDE_KO.md](LAB_1_5_GUIDE_KO.md)에 각 명령·기대 출력·ACCEPT 조건이 있다. Ubuntu 24.04/Jazzy에서 `git rev-parse HEAD`와 `ros2 doctor --report`, 전체 명령 로그·exit code를 보존한 다음에만 EXECUTION_ACCEPT 판단을 할 수 있다. Ch12의 과거 Gazebo/MuJoCo 테스트 실적을 Ch01에 인용해 통과 처리하지 않는다.

## 참고
- [Jazzy 공식 패키지 생성](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html)
- [Jazzy 공식 워크스페이스 생성](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html)
