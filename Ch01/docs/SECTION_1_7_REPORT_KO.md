# SECTION 1.7 — package.xml, setup.py, rosdep 의존성 관리 리뷰

- 작성: 2026-10-20 KST
- 기준 main: `f5aed1d250563efc298e717559497db3b4f205c7`
- 브랜치: `feat/ch01-section-1-7`
- 원고 범위: 1.7.1 `package.xml` → 1.7.2 `rosdep` → 1.7.3 `setup.py`, `data_files`, `console_scripts`.
- 상태: **MANUSCRIPT_ALIGNED / STATIC_REVIEWED / ROS_RUNTIME_NOT_RUN**.

## 1. 실습 대상 파일 매핑

| 원고 항목 | 저장소의 실제 파일 | 확인 내용 |
|---|---|---|
| ROS 의존성 명세 | `Ch01/robot_ws/src/my_robot_controller/package.xml` | `ament_python`, `rclpy`, `std_msgs`, 테스트 의존성 |
| ament_python 설치 | `Ch01/robot_ws/src/my_robot_controller/setup.py` | 패키지 등록 resource, `package.xml` 설치, `test_node` entry point |
| 스크립트 경로 | `Ch01/robot_ws/src/my_robot_controller/setup.cfg` | `lib/my_robot_controller` 설치 위치 |
| 실제 Python import | `Ch01/robot_ws/src/my_robot_controller/my_robot_controller/simple_controller.py` | `rclpy`와 `Node` import, `std_msgs` 직접 미사용 |
| 보조 패키지 | `Ch01/ref/{package.xml,setup.py,setup.cfg}` | `my_first_package`의 `rclpy`·`geometry_msgs` 의존성과 executable (`simple_node`, `cmd_publisher`) |
| 원고의 가상 `my_ai_robot_pkg` | **저장소에 없음** | OpenCV/NumPy/launch/config 설명을 위한 예제 스니펫일 뿐 실제 패키지가 아님 |

## 2. 문제 발견 및 변경/권고

| ID | 중요도 | 관찰 | 해결 및 판정 |
|---|---|---|---|
| 17-01 | High | 이전 리뷰에서 Twist 발행을 **1.7절 중심 실습**으로 설정했으나 원고는 패키징·의존성 관리 절 | **수정:** `my_robot_controller` 기준 `rosdep`·`package.xml`·`setup.py` 실습으로 전면 교체 |
| 17-02 | Medium | 원고의 `my_ai_robot_pkg`와 OpenCV·NumPy·launch·config 구조가 실제 Ch01 구현처럼 오해될 수 있음 | **문서화:** 교육용 스니펫으로 구분, 임의 디렉터리 생성·빌드 PASS 주장 금지 |
| 17-03 | Medium | 원고의 `rosdep install --from-paths src --ignore-src -r -y`는 의존성 전체를 대상으로 하므로 대규모 `examples` 트리에서 불필요한 설치 증가 | **가이드:** 세 개 핵심 패키지와 별도 workspace 기준으로 실행 |
| 17-04 | Medium | `std_msgs`가 manifest에 선언되었으나 `SimpleController`는 현재 import하지 않음 | **OPEN:** 다음 절에서 사용할 의존성인지 교육 목적 설명·정리 |
| 17-05 | Medium | `my_robot_controller`의 setup.py·package.xml에 설명·라이선스 TODO가 있음 | **OPEN:** 저작권자의 라이선스 판단 뒤 manifest 확정. 임의 Apache 표기 금지 |
| 17-06 | High | `Ch01/ref`에 `setup.cfg`가 없어 별도 예제의 `ros2 run` 설치 위치 불일치 가능 | **이미 보완됨:** 이 브랜치에 `Ch01/ref/setup.cfg` 추가. 주교재 `my_robot_controller`는 원래 갖춤 |
| 17-07 | Medium | 원고의 `glob('launch/*.launch.py')`/`glob('config/*.yaml')`는 `my_ai_robot_pkg` 가상 예시이며 실제 `my_robot_controller`에는 launch/config가 없음 | **문서화:** 없는 자산의 설치 테스트는 할 수 없음. 실제 디렉터리 생성 후 data_files에 연결하고 테스트해야 함 |
| 17-08 | Medium | `setup.py`의 `install_requires=['setuptools']`만으로 ROS 2의 apt/rclpy 종속성이 해결된다고 생각할 위험 | **교정:** ROS 의존성은 `package.xml`과 rosdep, Python 설치 메타데이터는 setup.py가 맡음 |
| 17-09 | Low | 원고에서 `--ignore-src`·`--from-paths` 옵션은 맞지만 최초 rosdep 초기화 설명 부족 | **가이드:** `rosdep update`/초기화 실패 진단 추가 |

## 3. 이전 브랜치의 비원고 코드 변경 정리

기존 1.7 브랜치에 포함되었던 `cmd_publisher_node.py`의 유한 발행/정지 동작 수정은 **원고 1.7의 필수 구현이 아니므로 원래 main 동작으로 복원**했다. 해당 Twist 예제는 책의 현재 1.7에서 직접 실습하지 않는다. 실제 로봇 구동에 연결할 때는 원본의 무한 비영 속도 발행을 금지하고, 격리된 토픽에서만 시험하도록 별도 안전 개선을 계획해야 한다. **이번 PR에는 변경된 안전 동작이 포함되어 있다고 주장하지 않는다.**

1.7 브랜치에 남긴 원본 코드 외 변경은 `Ch01/ref/setup.cfg`와 **두 문서**이며, `main`이나 1.6 주교재 코드에는 영향을 주지 않는다.

## 4. 검증 상태

| 검사 | 판정 |
|---|---|
| `package.xml`와 `setup.py`의 패키지 이름·실행파일 교차 검토 | **REVIEWED** |
| `setup.cfg` 및 `resource` 등록 경로 확인 | **REVIEWED** |
| `rosdep` 의존성 실질 설치/해결 | **NOT_RUN** |
| `colcon build --symlink-install` | **NOT_RUN** |
| `ros2 run my_robot_controller test_node` 및 `ros2 pkg executables` | **NOT_RUN** |
| OpenCV·NumPy·launch/config 가상 패키지 설치 | **OUT_OF_SCOPE / NOT_IMPLEMENTED** |

리뷰 환경에 ROS 2 및 colcon이 없으므로 PASS를 추측하지 않았다. 공식 Jazzy 문서 [패키지 생성](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html)의 ament_python 기본 패키지 구조와 비교했다.

## 5. Acceptance

[LAB_1_7_GUIDE_KO.md](LAB_1_7_GUIDE_KO.md)를 Ubuntu 24.04/Jazzy에서 실행한다. **ACCEPT:** rosdep 종속성 해결, `my_robot_controller` 선택 빌드, `test_node` 등록·실행, `package.xml`의 `rclpy` 의존성과 setup.py entry point 설명, 패키지 공유 파일 경로 탐색. **NOT_RUN**은 실제 로그 확보 전 유지한다. PR은 사용자가 독립적으로 생성한다.
