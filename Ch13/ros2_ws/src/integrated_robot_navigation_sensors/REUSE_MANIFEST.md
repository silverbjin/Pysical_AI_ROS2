# Ch13 navigation sensing 출처와 경계

이 패키지는 13.5절을 위해 작성한 Apache-2.0 코드다. 외부 checkout과 앞 장 원본은 수정하지 않는다.

| 대상 | 참조·재사용한 출처 | 고정 기준 / 방식 |
|---|---|---|
| 플러그인 base ABI | `mujoco_ros2_control_plugins` | 외부 underlay commit `c261f5552edf124d1000a23fb25b6c07cadeb807`; 헤더에 link, 원본 복사·수정 없음 |
| `SnapshotChannel` / worker | Ch13 `integrated_robot_camera`의 소유권 패턴 | 기준 commit `8e07b05cdf45eeb96dffbfe4fdbe1cf045373146`; 새 구현. 렌더링용 `mjv_copyData`를 복사하지 않고 **전체 `mj_copyData`**와 독립 모델 clone 사용 |
| `navigation_sensor_probe.cpp` | Ch13 `integrated_robot_camera/src/camera_plugin_probe.cpp` | 같은 기준 commit의 pluginlib 로드 검사 패턴을 최소 적응. ROS/GL 초기화 없이 실제 library 경로와 header/runtime version 출력 |
| `LICENSE` | Ch13 camera 패키지 Apache-2.0 전문 | 라이선스 본문 그대로 보존 |
| CMake source manifest | 같은 camera 패키지의 build-time provenance 블록 | 같은 기준 commit에서 sensor 입력 경로에 최소 적응; 빌드 시점 소스와 설치 .so의 출처 대조용 |
| MuJoCo native API | [3.12.0 공식 API](https://mujoco.readthedocs.io/en/3.12.0/APIreference/APIfunctions.html) | 실제 ROS C++ vendor는 3.12.0. 오프라인 Python 3.3.7과 구분. header/library 불일치 시 거절 |
| Gazebo 관측 API | 설치된 gz-sim8 헤더, [Physics.cc](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/physics/Physics.cc), [Contact.cc](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/contact/Contact.cc) | `ContactSensorData` 생성은 관측 요청이며 물리 명령이 아님. 실제 ECM 링크 관성·세계 pose를 읽음. 외부 구현 코드 복사 없음 |
| Gazebo 힘 좌표 계약 | [gz-physics7 GetContacts.hh](https://github.com/gazebosim/gz-physics/blob/gz-physics7/include/gz/physics/GetContacts.hh) | ExtraContactData 힘은 세계 좌표. 접촉 pair 미러링 시 collision 순서와 force 원래 방향을 동일시하지 않음 |

## 안전·수명 계약

- `update`에서 받은 안정된 control snapshot만 읽는다. live 상태 쓰기, root pose/속도 설정, 외력 plugin을 사용하지 않는다.
- worker는 모델 clone과 완전한 데이터 슬롯을 소유한다. 대기 프레임 덮어쓰기는 lease 슬롯을 변경하지 않는다.
- stop은 새 제출·발행을 차단한 다음 worker를 join한다. reset/clock rollback은 이전 frame을 무효화하고 **재시작을 요구**한다. 자동 재활성화하지 않는다.
- stop 서비스의 성공은 worker 정리만 의미한다. 엔진 정상 종료·부모 회수·잔여 없음은 별도 실제 실행 증거가 필요하다.
- MuJoCo scan은 robot group1만 제외하며 world geometry를 유지한다. Gazebo camera visibility는 유지하고 lidar mask1에서만 robot visual group2를 제외한다.
- `/navigation/native_com`의 PoseStamped는 **position에 CoM 점**을 넣는 bridge 공통 운반 형식이다. 로봇 pose나 TF 발행자가 아니다. identity orientation은 의미 없는 운반 값이다.
- ROS `FootContacts`는 odom/world 일치가 선언된 평지 benchmark에서 세계 +z 하중을 N 단위로 보고한다. 임의 경사면·등반 능력이나 실제 G1 센서 정확도 통과를 주장하지 않는다.

## 검증 해석

코어 fixture의 실제 물리 kernel 시험, ROS 플러그인 발행 시험, ECM 시험은 각각 기록한다. 이 시험 통과는 전체 로봇 G1/G2 또는 Nav2 종단 성공을 대체하지 않는다. 실제 엔진 인수는 별도 runner에서 수행한다.
