# Ch13 13.2 재사용·출처 명세

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
# Ch13 재사용 명세

기준 커밋: `1451f54a64374f2ff150a39429cc89e9e3b07696` (silverbjin/Pysical_AI_ROS2). 아래 경로는 모두 저장소 상대 경로다. Ch05~Ch12 원본은 수정하지 않았다. Ch13 실행에는 이전 장 import/overlay가 없다.

| 원본 | Ch13 대상 | 재사용 방식·수정 이유 | 원본 라이선스 상태 |
|---|---|---|---|
| Ch11/ros2_ws/src/my_quadruped_bot/urdf/common/robot_properties.xacro 및 parts/leg.xacro | ros2_ws/src/ch13_robot_description/urdf/quadruped_base.urdf.xacro, 공통 inertia, MJCF | 몸체 .60×.30×.15m, 6kg, 다리 .25m·질량·축·한계 개념을 재작성. 초기 1.2/-2.4 origin 회전을 없애 명시적 nominal과 일치시킴. 관성은 실제 primitive 중심으로 교정 | package.xml은 TODO. 허가가 확인된 외부 모델로 오인하면 안 됨 |
| Ch08/ros2_ws/src/my_robot_description/urdf/my_robot_6D.urdf.xacro | ros2_ws/src/ch13_robot_description/urdf/arm_6dof.urdf.xacro, MJCF | Z-Y-Y-X-Y-Z 순서만 채택, 무거운 .5m 링크 대신 경량 .06/.16/.14/.04/.04/.04m primitive 새 구현, 손가락/TCP 명명 통합 | package.xml은 TODO. 원본 메쉬 복사 없음 |
| Ch12/src/quadruped_rl/ros_core.py | src/ch13_sim_core/locomotion_core.py | 파일 복사, 출처 docstring 추가. 이름 정렬·freshness·48D 관측·출력 제한 유지. 새 locomotion_contract가 Ch13 설치 계약을 주입 | 원본 ROS package 선언 Apache-2.0, Ch13/LICENSE 보존 |
| Ch12/ros2_ws/src/quadruped_rl_ros/quadruped_rl_ros/rl_controller.py | ros2_ws/src/ch13_control/ch13_control/rl_leg_controller.py | 제어 루프·20ms 예산 설계 참고, 최소 어댑터로 재작성. 직접 Gazebo 모터 발행 제거, 다리 그룹만 발행, optional model loading | 원본 package 선언 Apache-2.0 |

Ch11/Ch08의 라이선스 TODO는 이 작업으로 해소하지 않았다. Ch13의 신규 코드 라이선스가 원본 전체나 외부 모델의 재배포 권리를 증명하는 것은 아니다. 외부 배포 시 저작권자 확인이 필요하다. 사용자 소유 저장소의 승인된 변경 범위에서 출처를 보존했다.

## 원본 파일 SHA-256 (기준 커밋 내용)

```text
26b9ba0fd0efadbc4e0a8523025b21b3c1a1f847ffff8970495bc1cb343436a5  Ch11/.../urdf/parts/leg.xacro
4e09d1f3d33e1f32585eda86d5729ffc073a06f606aa249da03989e8e4a9f733  Ch11/.../urdf/common/robot_properties.xacro
c842b5bab991c86329b361756e0cb5989cc7c0f8d07c55a6219fcf1ffb22c07e  Ch08/.../urdf/my_robot_6D.urdf.xacro
1a10b04275245d03f4ee77e5c02f47626ee7c4366ca722a566397b76bd4f1f0d  Ch12/src/quadruped_rl/ros_core.py
51ed3a23bc5d525844af351895fda8859db17c46a6ab748856ecff0f1ae7b491  Ch12/.../quadruped_rl_ros/rl_controller.py
```

## Ch13 재작성·복사본 SHA-256

```text
d710cbd2a5045a1adfa1aedcdcecda86997d39a30c928697729f7afff0cbebc5  ros2_ws/src/ch13_robot_description/urdf/quadruped_base.urdf.xacro
2d06e443217ce19ea8d38986c8fd95c6e6414858aae425973e4e6dc4b14c023e  ros2_ws/src/ch13_robot_description/urdf/arm_6dof.urdf.xacro
a5b246e03ea3a331ed7153aec6cd6df966b21f8570725c7c61bf2433b740f0a4  src/ch13_sim_core/locomotion_core.py
4ca45b3fae9d0acc39bc7dfd5cb55c39dd7ce94cf51f0fa7c70eb3694293983a  ros2_ws/src/ch13_control/ch13_control/rl_leg_controller.py
```

전체 최종 소스 해시는 evidence/verification_summary.json의 source_sha256가 기록한다. 이후 수정된 파일은 그 해시와 변경 보고서를 우선한다. 오류·draft·백업 접미 파일, Ch05/Ch06의 5축 MoveIt 설정, Ch11/Ch12 build/install/log, 기존 정책 가중치는 복사하지 않았다.
