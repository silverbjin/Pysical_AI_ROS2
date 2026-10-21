# LAB_7_3_GUIDE_KO — 7.3절 cv_bridge를 활용한 ROS 2와 OpenCV 통합

> **2026-10-21 코드 수정 반영 안내:** `ros2 run vision_basics vision_processor`는 GUI 기본 OFF입니다. 디스플레이가 준비된 경우에만 `--ros-args -p show_gui:=true`를 사용하십시오. 수정 범위와 정적 테스트는 [SECTION_7_3_FIX_TEST_REPORT_KO.md](SECTION_7_3_FIX_TEST_REPORT_KO.md)를 참조하세요. 본 가이드에 과거의 `BLOCKED`·미등록 안내가 있다면 **수정 전 리뷰 기록**이며, 현재의 ROS 빌드·실행 성공을 의미하지 않습니다.

> 대상: Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic, Ch07 단독 실습
> 기준 commit: a318c04a69a003e5c5d5998f077f2b8a8f36a1a5 (2026-10-20) · 상태: **BLOCKED — 변환 코드는 있으나 실습 결선 미완성**
> 실제 실행 검증: **미수행**. 아래 코드는 교재 실습 절차 및 실행 후 검증 기준이며, 출력 사례를 실측 결과로 제시하지 않는다.

## 실습 전 원칙
- 리포지토리 루트의 **Ch07/ros2_ws**를 작업 공간으로 사용한다. 설치된 패키지명은 **vision_basics**이다(원고의 my_robot_vision과 다름).
- 터미널마다 /opt/ros/jazzy/setup.bash → Ch07/ros2_ws/install/setup.bash 순서로 source한다. Ch08~Ch13 overlay가 AMENT_PREFIX_PATH에 섞이면 검증 결과가 바뀔 수 있다.
- 실제 카메라, 액션 서버, Gazebo controller, MoveIt 2 설정은 **존재 확인이 완료된 후** 해당 노드나 미션을 실행한다.
- ROS 관련 Python 바인딩은 Ubuntu/ROS apt 패키지를 우선한다. 글로벌 pip 설치가 ROS의 NumPy/Qt ABI와 충돌하지 않도록 주의한다.
- Gazebo에서의 노드 실행, 실제 팔/그리퍼 명령은 사람이나 실물 하드웨어가 없는 독립 시뮬레이션에서만 검증한다.

## 실행 전 패키지 환경
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
sudo apt install ros-jazzy-cv-bridge python3-opencv
python3 -c 'import cv2, numpy, cv_bridge; print(cv2.__version__)'
ros2 pkg executables vision_basics
~~~

이 저장소의 setup.py에는 vision_processor 엔트리가 등록되지 않았다. **수정하지 않고 ros2 run vision_basics vision_processor를 실행하면 실패할 수 있다.** 설치된 Python 모듈 경로를 검증한 뒤 임시로 python3 -m vision_basics.vision_processor를 사용하거나 엔트리를 등록한다.

## 카메라 없이 검증하는 최소 변환 스모크 테스트
~~~bash
python3 - <<'PY'
import numpy as np, cv2
from cv_bridge import CvBridge
bridge = CvBridge()
src = np.zeros((48,64,3), np.uint8)
src[10:35,15:47] = (0,0,255)
msg = bridge.cv2_to_imgmsg(src, encoding='bgr8')
dst = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
assert np.array_equal(src, dst)
gray = cv2.cvtColor(dst,cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(cv2.GaussianBlur(gray,(5,5),0),50,150)
assert edges.shape == (48,64) and edges.any()
print('cv_bridge round-trip + Canny PASS')
PY
~~~

## 실제 토픽 연결(7.2 센서 검증 이후)
~~~bash
ros2 topic info -v /camera/image_raw
# 엔트리 수정 후 사용
ros2 run vision_basics vision_processor
# 별도 터미널
ros2 topic echo --once /camera/processed_image --field encoding
ros2 topic hz /camera/processed_image
ros2 run rqt_image_view rqt_image_view
~~~

GUI가 없는 세션에서는 기존 cv2.imshow가 실패할 수 있다. RQt는 GUI 터미널에서 실행하고 노드의 GUI 호출을 비활성화하는 수정이 선행되어야 한다.

**완료 기준:** 위 독립 변환 테스트 통과, 입력/출력 토픽 모두 존재, mono8·header.stamp 유지, no-display 처리 확인. 실제 ROS 런타임 결과는 아직 미확인이다.

## 기록·제출물
실습자는 git rev-parse HEAD, ros2 doctor --report, colcon build 종료 코드, 실행한 명령, topic/TF/action 확인 결과, 정상 및 실패 사례(스크린샷·로그)를 함께 남긴다. **정적 점검 결과와 실측 결과를 혼동하지 않는다.**

관련 리뷰: [SECTION_7_3_REPORT_KO.md](SECTION_7_3_REPORT_KO.md).
