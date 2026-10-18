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
