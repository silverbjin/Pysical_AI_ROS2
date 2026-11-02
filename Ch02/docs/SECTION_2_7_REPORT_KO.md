# SECTION 2.7 론치 및 리매핑 코드 리뷰·수정 보고서

- **원고** 2.7.1~2.7.5 / **기준** `main@94264bee4b53ce4c9676011b98e72368b1e40690` / 2026-10-20.
- **검토 대상** `launch/my_turtle.launch.py`, `launch/remap_test.launch.py`, `setup.py`, 보조 실습 파일 `turtle_patrol.py`.
- **종합**: 기존 중단 실습을 보존하면서 **정상 연결용 론치 추가**. 별도 데모의 시작점 초기화 오류 수정. 실제 GUI 실행 미검증.

## 진단 결과

| ID | 등급 | 증거·영향 | 처리 |
|---|---|---|---|
| 2.7-01 | **의도적 실패** | `remap_test.launch.py`에서 발행자만 `/cmd_vel_custom`으로 바꾸어 turtlesim이 여전히 원래 토픽을 듣고 거북이가 움직이지 않음 | 원고의 실패 체험 용도로 보존하고 성공 버전 `remap_fixed.launch.py` 별도 추가 |
| 2.7-02 | Medium | 원고의 `OnProcessStart`는 **프로세스 시작** 이벤트이지 `/spawn` 서비스 준비를 의미하지 않음 | 론치 이벤트와 서비스 `wait_for_service`를 구분하는 가이드 추가 |
| 2.7-03 | Medium | `turtle_patrol.py`가 첫 `Pose`가 도착하기 전에 기본 `Pose()`(0,0)를 시작점으로 삼아 첫 콜백에서 잘못된 2m 이동 판정 가능 | 실제 첫 Pose 수신을 받은 다음 `start_forward_motion()` 호출 |
| 2.7-04 | Medium | `setup.py`의 glob(`launch/*.py`)은 새 파일 등록을 자동 수행하지만 빌드/재 source 없으면 `ros2 launch`에서 파일을 찾지 못할 수 있음 | 빌드·source 재수행 안내 |
| 2.7-05 | Low | 원고 “론치 파일에서 실행 순서를 지정한다”는 표현이 토픽·서비스 서버 준비 순서까지 보장한다고 오해할 가능성 | 반환 목록 순서만으로 노드 readiness는 보장하지 않음 |
| 2.7-06 | Info | `my_turtle.launch.py`는 turtlesim/publisher/subscriber 3노드 구성과 setup.py entry_points가 일치 | 변경하지 않음 |

## 수정 내역
- **추가**: `Ch02/ros2_ws/src/my_robot_system/launch/remap_fixed.launch.py` — 발행자·turtlesim 양쪽 `cmd_vel` 리매핑과 구독자·배경 파라미터.
- **수정**: `turtle_patrol.py` — 첫 Pose 이전 초기화를 막음. 이는 현재 2.7 원고에 없는 보조 코드이며 **정상 순찰 완료**를 증명한 수정은 아님.
- **유지**: `remap_test.launch.py` (학습용 비연결 상태), `my_turtle.launch.py` (기준 성공 상태).

## 검증 현황

| 검증 | 결과 |
|---|---|
| Python import·실행 파일 이름 및 remapping 쌍 정적 점검 | PASS (정적) |
| launch 파일 자동 설치 조건 glob 확인 | PASS (정적) |
| `ros2 launch` 실제 세 프로세스 기동 | NOT RUN |
| 끊김/복구 `topic info -v` 측정 | NOT RUN |
| turtlesim 창·좌표 이동·파라미터 색상 | NOT RUN |
| turtle_patrol 2m 직진/90도 회전 장기 테스트 | NOT RUN |

```bash
cd ~/Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch my_robot_system my_turtle.launch.py
# 별도 실행에서는 기존 프로세스 종료 후:
ros2 launch my_robot_system remap_test.launch.py
ros2 launch my_robot_system remap_fixed.launch.py
```

다른 장의 `my_robot_system` 패키지를 먼저 source하면 **이 장의 launch 파일 대신 이전 장 설치 파일이 참조**될 수 있다. `ros2 pkg prefix my_robot_system`과 `AMENT_PREFIX_PATH` 확인. 2.3절 의존성 변경 및 2.5절 action_msgs 빌드 수정이 선행되어야 함. 최종 Acceptance는 `PENDING_RUNTIME_VERIFICATION`.