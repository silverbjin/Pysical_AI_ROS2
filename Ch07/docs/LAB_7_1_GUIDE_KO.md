# LAB_7_1_GUIDE_KO — 7.1절 로봇 비전의 개요와 실무 적용 분야

> **2026-10-21 코드 수정 반영 안내:** 기존 명령은 저장소 패키지명 `vision_basics` 기준으로 실행합니다. `ros2 pkg executables vision_basics`로 5개 신규 엔트리를 먼저 확인합니다. 수정 범위와 정적 테스트는 [SECTION_7_1_FIX_TEST_REPORT_KO.md](SECTION_7_1_FIX_TEST_REPORT_KO.md)를 참조하세요. 본 가이드에 과거의 `BLOCKED`·미등록 안내가 있다면 **수정 전 리뷰 기록**이며, 현재의 ROS 빌드·실행 성공을 의미하지 않습니다.

> 대상: Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic, Ch07 단독 실습
> 기준 commit: a318c04a69a003e5c5d5998f077f2b8a8f36a1a5 (2026-10-20) · 상태: **REVIEWED — 개념 절, 통합 실행 미검증**
> 실제 실행 검증: **미수행**. 아래 코드는 교재 실습 절차 및 실행 후 검증 기준이며, 출력 사례를 실측 결과로 제시하지 않는다.

## 실습 전 원칙
- 리포지토리 루트의 **Ch07/ros2_ws**를 작업 공간으로 사용한다. 설치된 패키지명은 **vision_basics**이다(원고의 my_robot_vision과 다름).
- 터미널마다 /opt/ros/jazzy/setup.bash → Ch07/ros2_ws/install/setup.bash 순서로 source한다. Ch08~Ch13 overlay가 AMENT_PREFIX_PATH에 섞이면 검증 결과가 바뀔 수 있다.
- 실제 카메라, 액션 서버, Gazebo controller, MoveIt 2 설정은 **존재 확인이 완료된 후** 해당 노드나 미션을 실행한다.
- ROS 관련 Python 바인딩은 Ubuntu/ROS apt 패키지를 우선한다. 글로벌 pip 설치가 ROS의 NumPy/Qt ABI와 충돌하지 않도록 주의한다.
- Gazebo에서의 노드 실행, 실제 팔/그리퍼 명령은 사람이나 실물 하드웨어가 없는 독립 시뮬레이션에서만 검증한다.

## 학습 목표와 시스템을 그리기
① RGB 영상은 2D 픽셀 그리드이며 깊이를 자동 포함하지 않음을 설명한다. ② detector가 얻은 (u,v,area)는 3D 위치가 아님을 구분한다. ③ 카메라 K·depth·TF·IK·제어 및 파지 확인의 역할을 화살표로 연결한다.

~~~text
Gazebo camera (Image + CameraInfo + depth)
    → cv_bridge/OpenCV → 검출(u,v,area,stamp)
    → depth + K → camera_optical_frame의 3D 표면점
    → TF2(촬영 시각) → base_link의 PointStamped
    → MoveIt 2 계획/실행 → gripper 제어
    → 접촉/물체 pose 확인 → 성공 또는 실패/복구
~~~

## 환경·코드 구조 탐색
~~~bash
# Ubuntu 24.04 / ROS 2 Jazzy 전제. Ch07 단독 overlay에서 실행
source /opt/ros/jazzy/setup.bash
cd Pysical_AI_ROS2/Ch07/ros2_ws
echo "$ROS_DISTRO"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | head -20
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --event-handlers console_direct+
source install/setup.bash
ros2 pkg prefix vision_basics
~~~
~~~bash
cd src/vision_basics
find . -maxdepth 3 -type f | sort
grep -n -A20 'console_scripts' setup.py
grep -R -n 'camera/image_raw\|target_pixel\|target_object' vision_basics/ launch/ urdf/ || true
~~~

관찰 항목: 원고의 my_robot_vision과 설치 패키지 vision_basics의 차이; 미구현 단계와 기존 코드의 역할. 이 절은 시뮬레이션 성공을 주장하는 절이 아닌 설계·코드 읽기 실습이다.

## 체크 질문
- 왜 픽셀 중심의 x=320을 로봇 좌표 X=0.320m로 해석할 수 없는가?
- 객체 모양의 중심과 gripper의 grasp pose가 다른 이유는?
- 타임스탬프 없이 최신 TF를 적용하면 움직이는 팔에서 어떤 오차가 나는가?

**완료 기준:** 각 토픽/메시지 타입/좌표계/단위를 스스로 연결하고, 미완성 항목을 7.2~7.7 작업 목록으로 작성한다.

## 기록·제출물
실습자는 git rev-parse HEAD, ros2 doctor --report, colcon build 종료 코드, 실행한 명령, topic/TF/action 확인 결과, 정상 및 실패 사례(스크린샷·로그)를 함께 남긴다. **정적 점검 결과와 실측 결과를 혼동하지 않는다.**

관련 리뷰: [SECTION_7_1_REPORT_KO.md](SECTION_7_1_REPORT_KO.md).
