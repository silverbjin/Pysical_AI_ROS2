# SECTION 2.3 코드 리뷰·의존성 수정 보고서

- **원고** 2.3.1~2.3.5 / **기준 main** `94264bee4b53ce4c9676011b98e72368b1e40690`
- **대상** `turtle_cmd_publisher.py`, `turtle_pose_subscriber.py`, `setup.py`, `package.xml`.
- **종합 판정**: 코드의 메시지·토픽·entry point는 정적으로 일치. 매니페스트 필수 런타임 의존성 누락을 수정함. 실제 ROS 2 빌드/GUI 테스트 미검증.

## 발견 사항

| ID | 등급 | 근거 | 조치 |
|---|---|---|---|
| 2.3-01 | High | `geometry_msgs/Twist` 및 `turtlesim/Pose`를 import하지만 `my_robot_system/package.xml`에 `geometry_msgs`, `turtlesim` 선언 누락 | `exec_depend` 추가 |
| 2.3-02 | Medium | 후속 2.8절의 `std_msgs/String`과 2.7절의 `launch`/`launch_ros` 런타임 의존성 및 2.6절 클라이언트의 직접 `action_msgs/GoalStatus` import 의존성도 누락 | 공통 패키지 매니페스트에서 함께 보완; 병합 선행 필요 |
| 2.3-03 | Medium | 원고의 `source install/setup.`은 명령 불완전 | `source install/setup.bash` 안내 |
| 2.3-04 | Medium | 거북이를 계속 원운동시키는 publisher를 실제 구동계에서 응용하면 종료 시 정지 명령이 보장되지 않음 | 이 실습을 turtlesim 전용으로 제한, 실제 모터에서는 watchdog 필요 |
| 2.3-05 | Low | `turtle_pose_subscriber`의 `self.subscription` 단독 표현식은 의미 없는 더미 코드 | 기능상 무해, 추가 변경 없이 유지 |
| 2.3-06 | Info | `10`은 QoS 프로파일의 keep-last history depth; “항상 최근 10개가 실제 전송된다”는 의미는 아님 | 개념 설명 수정 |

## 변경 파일
`Ch02/ros2_ws/src/my_robot_system/package.xml`에 `geometry_msgs`, `turtlesim`, `std_msgs`, `action_msgs`, `launch`, `launch_ros` 실행 의존성을 선언했다. publisher/subscriber 코드와 공개 토픽 명칭은 변경하지 않았다.

## 검증 로그 구분
- PASS(정적): 경로·import·package entry_points 매칭, 주기 0.5초, pub `/turtle1/cmd_vel`/sub `/turtle1/pose` 대조.
- NOT RUN: `rosdep install`, `colcon build`, turtlesim GUI, `rqt_graph`, 초당 메시지 수 확인.
- 실행 근거 부재로 Acceptance=**PENDING_RUNTIME_VERIFICATION**.

```bash
cd ~/Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 pkg executables my_robot_system
ros2 interface show turtlesim/msg/Pose
```

## 병합 관계
이 PR은 2.3절 자체 및 **후속 2.7, 2.8절**의 공통 패키지 의존성을 보완한다. `main`에 이 변경을 병합한 뒤 2.7·2.8의 런타임 검증을 수행하는 것을 권장한다.