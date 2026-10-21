# LAB_7_5_GUIDE_KO — 7.5절 2D 픽셀 좌표의 3D 공간 좌표 변환

> **2026-10-21 코드 수정 반영 안내:** `ros2 run vision_basics coord_transformer --ros-args -p use_sim_time:=true`를 사용하되, 실제 CameraInfo·aligned depth·광학 프레임과 TF를 검증해야 합니다. 가짜 깊이값이나 과거 픽셀은 자동 사용되지 않습니다. 수정 범위와 정적 테스트는 [SECTION_7_5_FIX_TEST_REPORT_KO.md](SECTION_7_5_FIX_TEST_REPORT_KO.md)를 참조하세요. 본 가이드에 과거의 `BLOCKED`·미등록 안내가 있다면 **수정 전 리뷰 기록**이며, 현재의 ROS 빌드·실행 성공을 의미하지 않습니다.

> 대상: Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic, Ch07 단독 실습
> 기준 commit: a318c04a69a003e5c5d5998f077f2b8a8f36a1a5 (2026-10-20) · 상태: **BLOCKED — 요구 변환 노드 경로 미확인**
> 실제 실행 검증: **미수행**. 아래 코드는 교재 실습 절차 및 실행 후 검증 기준이며, 출력 사례를 실측 결과로 제시하지 않는다.

## 실습 전 원칙
- 리포지토리 루트의 **Ch07/ros2_ws**를 작업 공간으로 사용한다. 설치된 패키지명은 **vision_basics**이다(원고의 my_robot_vision과 다름).
- 터미널마다 /opt/ros/jazzy/setup.bash → Ch07/ros2_ws/install/setup.bash 순서로 source한다. Ch08~Ch13 overlay가 AMENT_PREFIX_PATH에 섞이면 검증 결과가 바뀔 수 있다.
- 실제 카메라, 액션 서버, Gazebo controller, MoveIt 2 설정은 **존재 확인이 완료된 후** 해당 노드나 미션을 실행한다.
- ROS 관련 Python 바인딩은 Ubuntu/ROS apt 패키지를 우선한다. 글로벌 pip 설치가 ROS의 NumPy/Qt ABI와 충돌하지 않도록 주의한다.
- Gazebo에서의 노드 실행, 실제 팔/그리퍼 명령은 사람이나 실물 하드웨어가 없는 독립 시뮬레이션에서만 검증한다.

## 좌표 수학 스모크(ROS 없어도 Python 실행)
영상 좌표 (u,v), 깊이 Z(m), 내부 파라미터 K를 이용한다. 예제 K는 **교육용 임의값**이며 카메라의 실제 측정값이 아니다.

~~~bash
python3 - <<'PY'
u,v=360.0,260.0
fx,fy,cx,cy=600.0,600.0,320.0,240.0
z=0.5
assert fx>0 and fy>0 and z>0
x=(u-cx)*z/fx; y=(v-cy)*z/fy
assert abs(x-0.0333333333333)<1e-9
assert abs(y-0.0166666666667)<1e-9
print('camera optical point (m):',x,y,z)
PY
~~~

## 코드 계약과 TF 점검
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
# 변환 노드 경로 확인
find src -type f \( -iname '*transform*.py' -o -iname '*coord*.py' \) | sort
ros2 topic type /camera/target_pixel
ros2 topic echo --once /camera/camera_info
ros2 topic echo --once /camera/depth/image_raw --field encoding
ros2 run tf2_ros tf2_echo base_link camera_optical_frame
~~~

원본 프로젝트에서 변환 노드와 카메라 구성이 확인되지 않으면 ROS 3D 변환 실습은 **진행 보류**한다. RGB만 존재한다면 원고의 고정 depth=0.5m를 실제 깊이로 간주하지 않는다.

## 구현 후 계측할 항목
- /camera/target_pixel은 header.stamp/frame_id를 보유해야 하며, 형식은 PointStamped 또는 명시적으로 정의한 커스텀 메시지여야 한다.
- 카메라 RGB/depth가 동일 광학 좌표계로 정렬되었는지 확인; 32FC1은 m, 16UC1은 보통 mm이며 장치 사양 기준.
- 시간 차이, depth 유효 픽셀 비율, TF age, invalid/stale 차단 횟수, 기준점 XYZ 절대 오차를 CSV에 남긴다.
- 변환 결과에는 base_link frame_id 및 캡처 stamp를 넣는다.

**완료 기준:** 깊이·K·TF 각 오류에 대해 잘못된 3D 목표가 발행되지 않고, 정적 기준점 오차가 정의한 허용치 안에 있음을 계측. 2mm 성능은 검증 전 주장하지 않는다.

## 기록·제출물
실습자는 git rev-parse HEAD, ros2 doctor --report, colcon build 종료 코드, 실행한 명령, topic/TF/action 확인 결과, 정상 및 실패 사례(스크린샷·로그)를 함께 남긴다. **정적 점검 결과와 실측 결과를 혼동하지 않는다.**

관련 리뷰: [SECTION_7_5_REPORT_KO.md](SECTION_7_5_REPORT_KO.md).
