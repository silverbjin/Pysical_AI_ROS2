# 4.2절 실습 가이드: 변하지 않는 센서 좌표 방송

**학습 목표:** `/tf_static`, transient-local QoS, static TF 한 번 전송과 다중 launch의 차이를 확인한다.

## 1. 환경 구축

Ubuntu 24.04/Jazzy, RViz GUI 사용. **이전 장 워크스페이스를 중복 source 하지 않은 새 터미널**에서 진행한다. 저장소를 이미 clone했다고 가정한다.

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch04/ros2_ws  # 저장소 위치에 따라 수정
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select my_robot_tf --symlink-install
source install/setup.bash
ros2 pkg executables my_robot_tf
```

`rosdep`, `colcon`이 없으면 Jazzy용 개발 도구를 설치한 뒤 다시 진행한다. GUI가 없으면 `tf2_echo`까지만 검증한다.

## 2. 실습 A: Python 단독 방송

터미널 1:

```bash
ros2 run my_robot_tf static_tf_broadcaster
```

터미널 2 (동일 환경 source):

```bash
ros2 run tf2_ros tf2_echo base_link lidar_sensor_link
ros2 topic echo --once --qos-durability transient_local /tf_static
ros2 topic info /tf_static -v
```

**기대 결과:** `base_link→lidar_sensor_link` 병진 x=0.1, z=0.2, quaternion w=1.0. `static_tf_broadcaster.py`는 `world`를 만들지 않으므로 RViz Fixed Frame은 `base_link`로 정한다. 프레임 이름은 `lidar_link`가 **아니다**.

## 3. 실습 B: 다중 정적 TF launch

실습 A를 Ctrl+C로 종료한 뒤 별도 테스트한다.

```bash
ros2 launch my_robot_tf multi_static_tf.launch.py
# 새 터미널
ros2 run tf2_ros tf2_echo world lidar
ros2 run tf2_tools view_frames
```

기대 트리: `world→base_link→lidar`. `world→base_link`는 z=1.0m, `base_link→lidar`는 (0.1,0,0.2)m이므로 **world 기준 lidar**는 (0.1,0,1.2)m, 회전 없음이다. 포함 RViz 설정의 Fixed Frame은 `world`.

## 4. 원고와 실제 코드의 프레임 이름 비교

| 실행 | 부모→자식 | 실제 이름 |
|---|---|---|
| 표준 CLI 예제 | `base_link→camera_link` | 원고 4.2.1 |
| Python 노드 | `base_link→lidar_sensor_link` | 실제 소스 |
| 다중 launch | `world→base_link→lidar` | 실제 소스·RViz |
| 원고에 기재된 `lidar_link` | 해당 코드에 없음 | 이름 오기 주의 |

프레임 이름이 다르다고 모두 고장난 것은 아니다. 다만 별도 프레임을 같은 센서라고 해석하면 잘못된 TF 조회를 하게 된다. 리팩터링 시 코드를 일관된 명명법으로 변경한다.

## 5. 실패 진단

- `frame does not exist`: 실제 `child_frame_id` 확인, 대소문자 확인, `ros2 topic echo` 점검.
- 설치 후 launch/RViz 파일을 찾지 못함: `source install/setup.bash`, `ros2 pkg prefix my_robot_tf`, `setup.py data_files` 확인.
- 늦게 붙은 터미널에서 정적 메시지가 안 보임: 발행자가 살아 있는지와 `transient_local` QoS 확인.
- RViz `Fixed Frame does not exist`: A는 `base_link`, B는 `world`.
- 통신 불가: `ROS_DOMAIN_ID`, `RMW_IMPLEMENTATION`, 활성 환경 중복 확인.

## 6. 실습 제출물과 통과 기준

`tf2_echo` 출력 2종, `view_frames` 그래프, RViz TF 화면, `/tf_static` QoS, 설치/실행 명령 기록. 데이터 실측이 없으면 '예상 결과'로 분류한다. **확장 과제:** 표준 CLI의 `--yaw 1.57079632679`를 적용했을 때 world 기준 자식 프레임이 어떻게 회전하는지 설명한다.

[리뷰 보고서](SECTION_4_2_REPORT_KO.md)
