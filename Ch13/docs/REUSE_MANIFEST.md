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
| `Ch05/ros2_ws/src/manipulation_basics/urdf/robot.urdf.xacro` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `1aa1277d230aff744413dc7f390096e9b7164fa8c84d22fe85304b5fac9e97db` | 팔 Xacro 분리와 링크 관성 작성 방식을 참고. 형상·이름은 새로 작성 |
| `Ch06/ros2_ws/src/my_robot_moveit_config/config/ros2_controllers.yaml` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `fb3c3ae27bc2513727ffb3b50da075f9e63d1d88477914b5b63438821139accd` | JointTrajectoryController 구성 관례 참고 |
| `Ch09/ros2_ws/src/my_quadruped_bot/urdf/robot.urdf.xacro` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `80f3a865746d3eb58a8a7a72c8395a1b4e1aada6e067ccf8d65863199321305e` | 4족 링크/관절 계층 참고. Ch13은 소문자 정규 이름과 새 원시 형상 사용 |
| `Ch09/ros2_ws/src/my_quadruped_bot/worlds/empty_world.sdf` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `0ede255c88a809562b3b66bfc5d84559b8c646157ad3965f4cd32560373e6591` | Gazebo 월드 시스템 구성을 참고해 Ch13 전용 월드 작성 |
| `Ch12/src/quadruped_rl/models/quadruped.xml` | `948718efa81b32708158c67815d8fe6b36aaec43` | `e76c2e9a3eae32e6818063cb0f102901c93c2c094edfb86e1a57c958e5f804e6` | MuJoCo 4족 계층·초기 자세와 위치 액추에이터 의미 참고 |
| `Ch12/src/quadruped_rl/ros_core.py` | `2077fd0b5f7fcaee8c003a9d57b5215253f33f88` | `1a10b04275245d03f4ee77e5c02f47626ee7c4366ca722a566397b76bd4f1f0d` | Ch12.8의 위치 잔차 명령 정책을 확인하는 용도. 코드 복사 없음 |

13.4에서 해시 기준을 **해당 커밋의 Git blob 바이트**로 통일했다. 위 Ch05/06/09 네 값은 이전 checkout 바이트 기준 값을 교정한 것이다. 원본 소스를 수정한 것이 아니다. Windows CRLF와 Git LF를 혼동하지 않는다. Ch12 두 값은 기존 값과 일치했다. 재현 시 checkout의 `sha256sum`만 비교하지 말고 다음처럼 blob을 읽는다.

```bash
git show 2077fd0b5f7fcaee8c003a9d57b5215253f33f88:Ch12/src/quadruped_rl/ros_core.py | sha256sum
git log -1 --format=%H -- Ch12/src/quadruped_rl/ros_core.py
```

## 외부 의존성

| 자산 | 고정 버전/커밋 | 사용 범위 |
|---|---|---|
| `ros-controls/mujoco_ros2_control` | `c261f5552edf124d1000a23fb25b6c07cadeb807` | `MujocoSystemInterface`, 전용 `ros2_control_node` |
| ROS 2 Jazzy `gz_ros2_control` | 설치된 Jazzy 패키지 | `GazeboSimSystem` |
| MuJoCo Python | 3.3.7 | 독립 MJCF 로드/적분 증거 |

외부 소스는 저장소에 복사하지 않고 `Ch13/ros2_ws/mujoco_ros2_control.repos`에서 커밋만 고정했다. 각 외부 프로젝트의 라이선스는 해당 원본 저장소를 따른다. 현재 상위 저장소에는 루트 라이선스 파일이 없으므로, Ch13 패키지의 `Apache-2.0` 메타데이터를 프로젝트 전체 라이선스 선언으로 확대 해석하지 않는다.

## 13.4 추가 명세

기준은 `df993e86d9b6ad446c058bc3b5a61c59c15495db`(13.3)이며 `feat/ch13-section-13-4`에서 작업했다. 이전 장 파일의 직접 복사는 없다. 다음 Ch07 자료는 개념만 참고했다. `.draft`, `.ok`, 백업, ZIP, 이전 build/install/log를 import하거나 실행하지 않았다. Ch13의 기존 소스는 같은 절 독립 패키지 안에서 확장했으며 외부 장 의존을 추가하지 않았다.

| 원본 경로 | 출처 최종 커밋 | Git-blob SHA-256 | 새 경로 / 변경·참고 범위 |
|---|---|---|---|
| `Ch07/ros2_ws/src/vision_basics/vision_basics/object_detector.py` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `61466950b6a2200c1810834995eb13e64e73450abc8ef957f8cfe8d580434ef5` | `Ch13/ros2_ws/src/integrated_robot_vision/integrated_robot_vision/detectors.py`：빨간색 fixture·원본 header 개념 참고. HSV/최대 contour 코드를 복사하지 않고 연결 성분·픽셀 중심 규칙을 새로 작성. YOLO와 별도 backend |
| `Ch07/ros2_ws/src/vision_basics/vision_basics/vision_processor.py` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `daf09773da3caf9e4ddb7909fc4eb5e7d19c996ee36577c3209c355cba5396b3` | 같은 새 패키지의 `object_detector.py`, `vision_processor.py`：cv_bridge·sensor QoS 참고. 원본 edge 처리와 달리 유계 작업자·RGB-D 정합·시간 계약을 새로 구현 |
| `Ch07/ros2_ws/src/vision_basics/vision_basics/coord_transformer_3_TF_frame.py` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `d0a215c63ff177b206da8670023d6dea192a056e6fe2ebf945e932a7ec8da95f` | 새 패키지의 `geometry.py`, `vision_processor.py`：CameraInfo/깊이/TF 분리 개념 참고. 촬영 시각 TF만 허용, 정합·단위·품질·TTL 추가. 타깃 TF broadcaster는 복사하지 않음 |
| `Ch07/ros2_ws/src/vision_basics/urdf/my_robot.ros2_camera_gazebo.xacro` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `eafada52cb90a99ea3d1d8d6aeaf856d4e17521c24d4d9ca630a3c8705d641a2` | `Ch13/ros2_ws/src/integrated_robot_description/urdf/`와 전용 센서 월드：센서 구성 관례만 참고. 원본 두 자유도 로봇·해상도·프레임을 가져오지 않음 |
| `Ch13/ros2_ws/src/integrated_robot_description/urdf/robot_system.urdf.xacro` | `0872b18f370047b464921d30a84494d968223a4a` | `0e24cb62dc3bcb2a683da92c774d478ed3d65727c204a0b8ca08382b2bacbfc3` | 같은 파일 확장：카메라 pitch -1.5708을 정확한 -π/2로 교정. 장착 위치·물리 질량 유지, vision opt-in 센서/optical frame 추가 |
| `Ch13/ros2_ws/src/integrated_robot_description/mujoco/robot_system.xml` | `0872b18f370047b464921d30a84494d968223a4a` | `9bc986c133e2a1ef3f1c541c952db09c2e66fb272c8d765c59e30ff36fc080a7` | 같은 모델 확장：20 관절/질량 구조 유지, URDF와 동일한 eye-in-hand 카메라 quaternion·센서 추가. 개별 엔진 geometry fixture는 별도 wrapper/world |
| `Ch13/ros2_ws/src/integrated_robot_runtime/integrated_robot_runtime/manipulation.py` | `df993e86d9b6ad446c058bc3b5a61c59c15495db` | `d88edc460cf37d85e54df78ce85e91b1606a867935a2ab28ad1f29897aa4dcb4` | 같은 노드 + `arm_action_owner.py`, `tracking_support.py`：stow와 tracking의 단일 세션/미완료 액션 소유권. 물리 pick으로 바꾸지 않음 |
| `Ch13/ros2_ws/src/integrated_robot_runtime/integrated_robot_runtime/common.py` | `df993e86d9b6ad446c058bc3b5a61c59c15495db` | `ac85116714f26b3732c4698518ca4a8f9a12b02dd2551875a0e35b3e44b2baa9` | 같은 파일：Jazzy executor 종료 순서·생성자/작업자 종료 처리. 새 vision의 `execution.py`는 별도 single-threaded callback/worker 수명 구현 |

Ch07 `package.xml`은 `TODO: License declaration`이다. 원본에 대한 사용·재배포 권리가 별도로 해결됐다고 주장하지 않는다. 여기서는 구현 본문을 복사하지 않았다. Ch13 패키지는 기존 자체 패키지의 Apache-2.0 메타데이터를 유지한다. 이 표는 라이선스 감사를 대체하지 않으며 상위 저장소 전체의 권리 문제를 해결하지 않는다.

### 13.4 외부 실행 자산

- ROS/C++ 플러그인 소스는 고정 외부 workspace에서 빌드하며 수정·vendor 복사하지 않았다. MuJoCo free joint는 선속도가 world, 각속도가 local이라는 설치 버전 계약을 Ch13 adapter에서 처리한다.
- Python 실행 버전은 `Ch13/requirements-vision-13-4.txt`와 각 실제 실행의 versions에 기록한다. CPU PyTorch 2.5.1/torchvision 0.20.1, Ultralytics 8.3.221, OpenCV 4.10.0.84를 사용했다.
- `yolov8n.pt` 출처는 공식 assets v8.3.0이며 SHA-256은 `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36`이다. `bus.jpg`는 공식 저장소 v8.3.221이며 `c02019c4979c191eb739ddd944445ef408dad5679acab6fd520ef9d434bfbc63`이다. URL·정확한 크기·권리 관련 원본 선언은 `Ch13/config/vision_assets.json`에 고정했다.
- Ultralytics/model의 AGPL-3.0 또는 별도 Enterprise 조건과 사진 권리는 배포 방식에 따라 별도 확인해야 한다. 본 저장소는 법적 허가를 보증하지 않는다. 모델·버스 원본·해당 주석 영상은 저장소에 넣지 않았다.
- 저장소에 보존한 native RGB/depth/주석 영상은 Ch13의 자체 원시 형상·단색 fixture를 실제 엔진에서 렌더링한 결과다. 합성 정답 영상을 카메라 토픽으로 주입한 것이 아니다.
- 실행 소스 목록/바이트 해시는 각 `source_snapshot.json`이다. 검증기가 생성한 build/install/log/cache/evidence는 소스 인벤토리에서 제외한다. 검증 코드와 최종 문서/evidence 커밋 SHA는 자기 참조를 피하기 위해 구분한다.
