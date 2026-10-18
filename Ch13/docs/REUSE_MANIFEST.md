# Ch13 13.2 재사용·출처 명세

13.3 추가: `integrated_robot_interfaces`, `integrated_robot_runtime`, 검증기와 정책
테스트는 새로 작성했다. 13.2 모델/launch 재사용 기준 커밋은
`8d7d7e0b6003845ad7e6ef77420cf35e16758202`이며 원본 파일을 직접 호출한다.
Ch05~Ch12 코드의 추가 복사는 없다. ROS 2 rclpy/message_filters는 설치된 외부
의존성으로 사용하며 그 소스를 패키지에 복사하지 않는다.

## 기준점

- 구현 시작 기준: `1451f54a64374f2ff150a39429cc89e9e3b07696`
- 기준 브랜치 당시 설명: `Merge pull request #15 from silverbjin/feat/ch12-section-12-8-separated`
- Ch05~Ch12는 읽기 전용 참고 자료로만 사용했으며 직접 수정하지 않음.
- 아래 파일을 Ch13으로 그대로 복사하지 않았다. 이름·관절 구성·제어 흐름을 참고해 Ch13용 원시 형상 모델과 테스트를 새로 작성했다.

## 내부 참고 자산

| 참고 자산 | 해당 파일 최종 커밋 | SHA-256 | Ch13 반영 방식 |
|---|---|---|---|
| `Ch05/ros2_ws/src/manipulation_basics/urdf/robot.urdf.xacro` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `3ea15c8f6680e2c74d5d17cb9ee17e6497d1fce82451d57be8395f204faa099e` | 팔 Xacro 분리와 링크 관성 작성 방식을 참고. 형상·이름은 새로 작성 |
| `Ch06/ros2_ws/src/my_robot_moveit_config/config/ros2_controllers.yaml` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `fd0a0a777c1b8c70003a9d66d4de5e35033d546ab9220f8e718cc02a664d98e1` | JointTrajectoryController 구성 관례 참고 |
| `Ch09/ros2_ws/src/my_quadruped_bot/urdf/robot.urdf.xacro` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `ddb75ba6df166a3780d57502335fc4f152b0d86ff90950d43e0daabf27d264a7` | 4족 링크/관절 계층 참고. Ch13은 소문자 정규 이름과 새 원시 형상 사용 |
| `Ch09/ros2_ws/src/my_quadruped_bot/worlds/empty_world.sdf` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `cc37d102c7a852dcac0be0ad797fdfd47cf6437168e7ee0d16c1c949e9d0bcbc` | Gazebo 월드 시스템 구성을 참고해 Ch13 전용 월드 작성 |
| `Ch12/src/quadruped_rl/models/quadruped.xml` | `948718efa81b32708158c67815d8fe6b36aaec43` | `e76c2e9a3eae32e6818063cb0f102901c93c2c094edfb86e1a57c958e5f804e6` | MuJoCo 4족 계층·초기 자세와 위치 액추에이터 의미 참고 |
| `Ch12/src/quadruped_rl/ros_core.py` | `2077fd0b5f7fcaee8c003a9d57b5215253f33f88` | `1a10b04275245d03f4ee77e5c02f47626ee7c4366ca722a566397b76bd4f1f0d` | Ch12.8의 위치 잔차 명령 정책을 확인하는 용도. 코드 복사 없음 |

해시는 구현 시점의 파일을 대상으로 계산했다. 재현 시 다음 명령으로 현 파일과 비교할 수 있다.

```bash
sha256sum Ch12/src/quadruped_rl/ros_core.py
git log -1 --format=%H -- Ch12/src/quadruped_rl/ros_core.py
```

## 외부 의존성

| 자산 | 고정 버전/커밋 | 사용 범위 |
|---|---|---|
| `ros-controls/mujoco_ros2_control` | `c261f5552edf124d1000a23fb25b6c07cadeb807` | `MujocoSystemInterface`, 전용 `ros2_control_node` |
| ROS 2 Jazzy `gz_ros2_control` | 설치된 Jazzy 패키지 | `GazeboSimSystem` |
| MuJoCo Python | 3.3.7 | 독립 MJCF 로드/적분 증거 |

외부 소스는 저장소에 복사하지 않고 `Ch13/ros2_ws/mujoco_ros2_control.repos`에서 커밋만 고정했다. 각 외부 프로젝트의 라이선스는 해당 원본 저장소를 따른다. 현재 상위 저장소에는 루트 라이선스 파일이 없으므로, Ch13 패키지의 `Apache-2.0` 메타데이터를 프로젝트 전체 라이선스 선언으로 확대 해석하지 않는다.
