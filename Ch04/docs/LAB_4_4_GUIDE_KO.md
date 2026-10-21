> 2026-10-21 반영: `tracking_demo.launch.py` 및 listener 프레임 파라미터가 추가됐다. 통합 launch 사용 시 수동 static publisher를 동시에 띄우지 않는다.

# 4.4절 실습 가이드: TF 리스너로 움직이는 프레임 추적

**목표:** 4.3절의 `turtle_frame` 위치를 `world` 기준으로 1초마다 읽고 평면 거리 2m를 검증한다. **기본 단독 실행은 `world` 기준**이지만, 새 `tracking_demo.launch.py`를 쓰면 `world→police_bot` 정적 TF를 자동으로 만들고 관측자를 `police_bot`으로 설정한다.

## 1. 환경·빌드

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch04/ros2_ws
colcon build --packages-select my_robot_tf --symlink-install
source install/setup.bash
ros2 pkg executables my_robot_tf
```

각 터미널에서 `source /opt/ros/jazzy/setup.bash`와 같은 워크스페이스 `source install/setup.bash`를 실행한다.

## 2. 통합 실행(권장) 및 두 노드 개별 실행

권장 명령(한 터미널):

```bash
ros2 launch my_robot_tf tracking_demo.launch.py
```

이 launch는 방송 노드, `world→police_bot` 정적 TF, `tf_listener`(`target_frame=police_bot`)를 함께 시작한다. 다음은 별도 단독 실행/디버깅용이다.


터미널 A (4.3 방송):

```bash
ros2 run my_robot_tf dynamic_tf_broadcaster
```

터미널 B (4.4 리스너):

```bash
ros2 run my_robot_tf tf_listener
```

터미널 C (독립 관찰):

```bash
ros2 run tf2_ros tf2_echo world turtle_frame
ros2 topic hz /tf
```

## 3. 예상 로그와 검증

```text
[INFO] [...] Detected: Turtle is at (1.xx, y.yy), Distance: 2.00m
```

이 로그는 **패턴 예시이며 실제 실행 기록이 아니다.** 좌표값은 계속 변하지만 반경이 일정하므로 평면 거리 `2.00m` 부근을 예상한다. 프레임 이름 `world`는 방송 노드의 부모이고 `turtle_frame`은 자식이다. 리스너는 `lookup_transform(target='world',source='turtle_frame',time=Time())`을 호출한다.

## 4. '경찰 로봇' 실험을 정확하게 확장하기

현재 `world` 원점에서 관찰하므로 '경찰 로봇이 world 원점에 있다'는 **개념 가정**이다. 통합 launch를 사용하지 않을 때 `police_bot` TF가 필요하다면 새 터미널에서 아래 명령을 실행한다.

```bash
ros2 run tf2_ros static_transform_publisher \
  --x 0 --y 0 --z 0 --roll 0 --pitch 0 --yaw 0 \
  --frame-id world --child-frame-id police_bot
ros2 run tf2_ros tf2_echo police_bot turtle_frame
```

`police_bot`을 world 원점과 동일하게 둔 상태에서는 world 기준 값과 동일해야 한다. Python 리스너의 코드를 수정하지 않고 `ros2 run my_robot_tf tf_listener --ros-args -p target_frame:=police_bot`으로 지정할 수 있다. 단독 실행의 기본값은 world다. 자식 `police_bot`을 이미 발행 중이면 중복 방송 금지.

## 5. 예외 및 시간 처리

- 방송 전에 listener만 켜면 처음에 `Could not transform` 로그가 예상된다. 프레임이 연결되면 다음 조회가 성공해야 한다.
- 방송을 종료해도 버퍼에 최근 데이터가 일부 남을 수 있다. '즉시 에러'를 합격 조건으로 삼지 않는다.
- `rclpy.time.Time()`은 특수한 최신 공통시각 요청이지 네트워크에서 정확히 지금 순간의 측정값을 요구하는 것이 아니다.
- 센서 프레임으로 조회할 때는 `Time.from_msg(msg.header.stamp)`를 이용하고, 시간원 `/clock`·`use_sim_time`를 통일한다. 동기 timeout을 콜백 안에서 남용하지 않는다.

## 6. 비교 실습과 제출물

`tf2_echo turtle_frame world` 역변환을 확인한다. 자식 프레임이 회전하고 있으므로 역변환 translation의 x,y가 단순히 정방향 값의 부호만 반대로 나오지 않을 수 있다.

| 검증 | 합격 조건 |
|---|---|
| TF 발행·수신 | `/tf`와 listener 로그 확인 |
| 거리 | 출력 2.00m 부근 유지 |
| 예외 처리 | 미수신 시 프로세스 정상 유지 |
| 확장 | `world→police_bot` 추가 후 동등한 결과 |
| 종료 | 두 Python 노드와 static CLI를 Ctrl+C로 정리 |

실행 OS/명령/`tf2_echo` 출력/대표 로그 5개/실패 로그를 남긴다. [4.4절 리뷰 보고서](SECTION_4_4_REPORT_KO.md).
