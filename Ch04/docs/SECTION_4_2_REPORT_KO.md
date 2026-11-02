# 4.2절 코드 리뷰: Static TF Broadcaster

- 기준: `main@7b7c10f` / 2026-10-20 KST / `feat/ch04-section-4-2`
- 대상: `Ch04/ros2_ws/src/my_robot_tf/my_robot_tf/static_tf_broadcaster.py`, `launch/multi_static_tf.launch.py`, `rviz/multi_static_tf.rviz`, `setup.py`, `package.xml`
- 판정: **핵심 Python 로직 정적으로 타당; 시각화·프레임 계약의 일관성 수정 권장**
- 증거: GitHub 파일 정적 검토. ROS/Jazzy/RViz 실기동, colcon 실행, 테스트 실행은 **NOT RUN**.

## 1. 코드 동작과 종속성

`StaticFramePublisher`는 `StaticTransformBroadcaster`를 생성하여 생성자에서 `base_link→lidar_sensor_link`, 병진 (0.1,0,0.2)m, 항등 회전을 **한 번** 전송한다. `setup.py`의 `static_tf_broadcaster` entry point는 등록되어 있고, `launch/`와 `rviz/` 설치 경로도 설정되어 있다. `package.xml`은 `rclpy`, `tf2_ros`, `geometry_msgs`를 선언한다.

별도 `multi_static_tf.launch.py`는 `world→base_link`, `base_link→lidar`를 **표준 CLI 노드** 2개로 띄우고 RViz를 연다. 이 두 실습은 서로 다른 자식 프레임을 사용한다.

## 2. 발견 결함 및 영향

| ID | 등급 | 재현·근거 | 영향과 조치 |
|---|---|---|---|
| 4.2-R1 | High | Python `lidar_sensor_link` vs launch·RViz `lidar`, 원고 `lidar_link` | 독자가 기대한 이름으로 TF를 조회하면 연결이 없다고 나온다. 일관된 명명 정책 하나를 선정하고 코드·RViz·본문 동기화. 현재 가이드에서는 **기존 실제 파일 이름** 그대로 분리하여 실행. |
| 4.2-R2 | Medium | Python 단독 노드는 `world→base_link`를 전송하지 않음 | Fixed Frame `world` 선택 시 연결 트리 없음. 단독 RViz는 Fixed Frame `base_link` 사용. |
| 4.2-R3 | Medium | launch의 `static_transform_publisher`에 위치 인수 8개를 구식 positional 형식으로 전달 | Jazzy에서는 명시적 `--x … --frame-id` 형식이 더 읽기 쉽고 향후 호환성이 높다. 기존 동작 여부는 실기동 확인 필요. |
| 4.2-R4 | Medium | 원고 4.2.3에는 `lidar_sensor_link` 기재, 실제 launch는 `lidar` | 독자는 `tf2_echo` 또는 RViz에서 프레임을 직접 확인하고 표기의 차이를 기록해야 한다. |
| 4.2-R5 | Low | `setup.py`와 `package.xml`의 TODO 메타데이터, 자동 TF 계약 테스트 부재 | 출판용 메타데이터·pytest 검증 추후 추가. 기능 오류와 구분. |

### 주의 사항

`/tf_static`은 transient-local 내구성 QoS로 늦게 접속한 리스너에 마지막 데이터를 제공한다. 단, 발행 노드가 종료된 뒤에도 영구적으로 값이 남는다는 뜻은 아니다. `ros2 topic echo /tf_static`가 늦게 붙었을 때 QoS 설정에 따라 과거 발행이 안 보일 수 있어 `--qos-durability transient_local`을 사용한다. static 메시지 재발행을 무한 루프에서 하는 방식은 채택하지 않는다.

## 3. Acceptance 조건

1. 빌드와 설치 후 `ros2 pkg executables my_robot_tf`에서 `static_tf_broadcaster` 노출.
2. **단독 Python 실습**: `tf2_echo base_link lidar_sensor_link`의 병진 `(0.1,0,0.2)`, quaternion `(0,0,0,1)`.
3. **별도 launch 실습**: `world→base_link→lidar` 트리와 RViz Fixed Frame `world` 일치.
4. 두 방식의 `lidar`/ `lidar_sensor_link` 차이를 인식하고 같은 TF를 중복 발행하지 않음.

## 4. 검증 현황

- 코드·entry point·자산 설치 선언: **정적 점검**
- `pytest`, `colcon build`, `tf2_echo`, `view_frames`, RViz: **NOT RUN**
- 실측 PASS로 단정 금지. [실습 가이드](LAB_4_2_GUIDE_KO.md)에 최소 재현법과 실패 판정 포함.

## 5. 링크

[현재 소스](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch04/ros2_ws/src/my_robot_tf) · [ROS 2 tf2 정적 broadcaster](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Static-Broadcaster-Py.html)
