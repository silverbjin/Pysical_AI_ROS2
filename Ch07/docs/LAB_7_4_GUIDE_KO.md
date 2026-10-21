# LAB_7_4_GUIDE_KO — 7.4절 OpenCV 기반 물체 인식 알고리즘 구현

> **2026-10-21 코드 수정 반영 안내:** `ros2 run vision_basics object_detector --ros-args -p min_contour_area:=500.0`으로 시작합니다. `/camera/target_pixel`은 `PointStamped`이나 x/y는 pixel이고 z는 면적(pixel²)이므로 3D 좌표로 사용하지 않습니다. 수정 범위와 정적 테스트는 [SECTION_7_4_FIX_TEST_REPORT_KO.md](SECTION_7_4_FIX_TEST_REPORT_KO.md)를 참조하세요. 본 가이드에 과거의 `BLOCKED`·미등록 안내가 있다면 **수정 전 리뷰 기록**이며, 현재의 ROS 빌드·실행 성공을 의미하지 않습니다.

> 대상: Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic, Ch07 단독 실습
> 기준 commit: a318c04a69a003e5c5d5998f077f2b8a8f36a1a5 (2026-10-20) · 상태: **BLOCKED — 검출 로직은 존재, 메시지/등록 계약 불일치**
> 실제 실행 검증: **미수행**. 아래 코드는 교재 실습 절차 및 실행 후 검증 기준이며, 출력 사례를 실측 결과로 제시하지 않는다.

## 실습 전 원칙
- 리포지토리 루트의 **Ch07/ros2_ws**를 작업 공간으로 사용한다. 설치된 패키지명은 **vision_basics**이다(원고의 my_robot_vision과 다름).
- 터미널마다 /opt/ros/jazzy/setup.bash → Ch07/ros2_ws/install/setup.bash 순서로 source한다. Ch08~Ch13 overlay가 AMENT_PREFIX_PATH에 섞이면 검증 결과가 바뀔 수 있다.
- 실제 카메라, 액션 서버, Gazebo controller, MoveIt 2 설정은 **존재 확인이 완료된 후** 해당 노드나 미션을 실행한다.
- ROS 관련 Python 바인딩은 Ubuntu/ROS apt 패키지를 우선한다. 글로벌 pip 설치가 ROS의 NumPy/Qt ABI와 충돌하지 않도록 주의한다.
- Gazebo에서의 노드 실행, 실제 팔/그리퍼 명령은 사람이나 실물 하드웨어가 없는 독립 시뮬레이션에서만 검증한다.

## 학습 목표
HSV wrapping과 형태학적 열림/닫힘을 설명하고, 빨간색 영역의 최대 콘투어에서 (u,v)를 계산한다. **PointStamped.point.z는 3D 깊이가 아니라 mask 면적(px²)** 임을 반드시 구분한다.

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
grep -n 'PointStamped\|area >\|inRange\|morphologyEx' src/vision_basics/vision_basics/object_detector.py
grep -A15 console_scripts src/vision_basics/setup.py
~~~

## 카메라 없이 빨강 검출 실험
~~~bash
python3 - <<'PY'
import cv2, numpy as np
im=np.zeros((240,320,3),np.uint8)
cv2.rectangle(im,(100,70),(180,150),(0,0,255),-1)
hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
m=cv2.bitwise_or(cv2.inRange(hsv,np.array([0,100,100]),np.array([10,255,255])),
                 cv2.inRange(hsv,np.array([170,100,100]),np.array([179,255,255])))
k=np.ones((5,5),np.uint8)
m=cv2.morphologyEx(cv2.morphologyEx(m,cv2.MORPH_OPEN,k),cv2.MORPH_CLOSE,k)
cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
c=max(cs,key=cv2.contourArea)
M=cv2.moments(c); cx=M['m10']/M['m00']; cy=M['m01']/M['m00']
assert abs(cx-140)<2 and abs(cy-110)<2
print('HSV centroid smoke PASS:',round(cx,2),round(cy,2),'area',cv2.contourArea(c))
PY
~~~

## ROS 검출 실습(노드 등록·영상 복구 이후)
~~~bash
ros2 run vision_basics object_detector
ros2 topic info -v /camera/target_pixel
ros2 topic echo --once /camera/target_pixel
ros2 run rqt_image_view rqt_image_view
~~~

관찰: 영상의 초록색 contour·중심점, 토픽의 header.frame_id/stamp, point.x/y=픽셀 좌표, point.z=면적(px²). 물체를 치웠을 때 이전 검출 좌표를 **유효 목표로 재사용하지 않는지** 하위 단계에서 확인한다.

**완료 기준:** 합성 이미지 중심 오차 2px 미만, 색상 경계 두 범위 검증, 실제 목표 0/1/2개 입력의 오검출·미검출 처리 기록. 서버 실행 PASS는 확인되지 않았다.

## 기록·제출물
실습자는 git rev-parse HEAD, ros2 doctor --report, colcon build 종료 코드, 실행한 명령, topic/TF/action 확인 결과, 정상 및 실패 사례(스크린샷·로그)를 함께 남긴다. **정적 점검 결과와 실측 결과를 혼동하지 않는다.**

관련 리뷰: [SECTION_7_4_REPORT_KO.md](SECTION_7_4_REPORT_KO.md).
