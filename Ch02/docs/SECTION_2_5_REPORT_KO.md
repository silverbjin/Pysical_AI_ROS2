# SECTION 2.5 코드 리뷰 및 인터페이스 빌드 점검 보고서

- **원고** 2.5.1~2.5.6 / **기준** `main@94264bee4b53ce4c9676011b98e72368b1e40690` / 검토일 2026-10-20.
- **검토 대상** `my_robot_interfaces/{CMakeLists.txt,package.xml,msg/HardwareStatus.msg,srv/ComputeRectangleArea.srv,action/CountUntil.action}`, `my_robot_system/hw_status_publisher.py`.
- **종합 상태**: 발견한 의존성 문제를 소스에서 수정. **실제 colcon/rosidl 빌드는 미검증**.

## 이슈별 판정

| ID | 심각도 | 원인·증거 | 조치 |
|---|---|---|---|
| 2.5-01 | **High / 빌드 차단 가능** | 현 저장소의 `rosidl_generate_interfaces`에는 `action/CountUntil.action`이 이미 등록되어 있으나 `my_robot_interfaces/package.xml`에 `action_msgs` `depend` 없음. rosidl 생성 시 액션 의존성 검사 실패 위험 | `<depend>action_msgs</depend>` 추가 |
| 2.5-02 | Medium | 원고 2.5절은 msg·srv까지만 제작하지만 실제 GitHub 인터페이스 패키지는 2.6의 action까지 동시에 생성함 | **절별 순차 작성**과 **현 저장소 전체 빌드**는 다름. 2.5에서도 action 종속성을 갖춰야 함을 명시 |
| 2.5-03 | Medium | 원고 `source install/setup.`은 잘린 명령 | `source install/setup.bash` 안내 |
| 2.5-04 | Medium | `ros2 pkg create --dependencies ... my_robot_interfaces my_robot_system`(2.1절)이 인터페이스 패키지 생성 전 실행되면 의존성이 미해결될 수 있음 | 저장소에 이미 존재하는 두 패키지를 **다시 생성하지 말고**, 현 소스 빌드 |
| 2.5-05 | Low | 원고 예시는 `HardwareStatus`에 ID·경고·문자열만 포함. 도입부의 4개 온도·전압·오류코드는 구현되지 않음 | **구현 범위는 3필드**임을 안내 |
| 2.5-06 | Info | `CMakeLists.txt`의 `rosidl_default_generators` 호출·msg/srv/action 경로와 Python import 패턴 적합 | 변경 없음 |

## 확인 가능한 사실
- `HardwareStatus.msg`: `int64 machine_id`, `bool temperature_warning`, `string debug_message`.
- `ComputeRectangleArea.srv`: `length`, `width` 요청, `area` 응답. 이를 처리하는 별도 Python 서비스 서버 코드는 **현재 저장소에 없음**. 이 절에서는 인터페이스 표시·직접 객체 생성으로만 검증한다.
- `hw_status_publisher.py`는 `hardware_status` 토픽에 ID=101, False, 정상 문자열을 1Hz 간격으로 발행하도록 구현됨.

## 검증 근거 및 미수행 항목

| 확인 | 상태 |
|---|---|
| .msg/.srv/.action 구조·CMake 등록/의존성 코드 대조 | PASS (정적) |
| 누락된 `action_msgs` 선언 추가 | PATCH APPLIED (런타임 효과 미검증) |
| `colcon build --packages-up-to my_robot_system` | NOT RUN |
| `ros2 interface show` 세 타입 및 Python 객체 생성 | NOT RUN |
| `ros2 topic echo /hardware_status` | NOT RUN |

```bash
cd ~/Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-up-to my_robot_system
source install/setup.bash
ros2 interface show my_robot_interfaces/msg/HardwareStatus
ros2 interface show my_robot_interfaces/srv/ComputeRectangleArea
ros2 interface show my_robot_interfaces/action/CountUntil
ros2 interface package my_robot_interfaces
```

## 병합 관련
**2.5절 PR을 2.6절 PR보다 먼저 병합**해야 2.6 액션 예제의 독립 빌드 의존성이 충족된다. 오버레이 충돌을 막기 위해 깨끗한 Ch02 워크스페이스와 `ros2 pkg prefix my_robot_interfaces`를 확인한다. 실행 로그가 확보되기 전 Acceptance는 `PENDING_RUNTIME_VERIFICATION`이다.

참고: ROS 2 공식 사용자 가이드 「Creating custom msg and srv files」, 「Creating an action」 및 rosidl 생성 도구의 의존성 검사.
