# 13.3 구현 및 리뷰 보고서

## 변경 범위

13.2 최종 커밋 `8d7d7e0b6003845ad7e6ef77420cf35e16758202` 위에
`feat/ch13-section-13-3` 브랜치를 생성했다. 새 interfaces/runtime 패키지와
통합 검증기를 Ch13에 추가했다. Ch05~Ch12는 변경하지 않았다.

기존 13.2 Xacro·MJCF·컨트롤러 매핑을 그대로 사용한다. 다리는 12개 position
command, 팔은 6개 trajectory action, 그리퍼는 2개 position command를 각각
별도 ros2_control 컨트롤러가 소유한다. 런타임 노드가 직접 hardware interface를
추가하거나 같은 관절의 별도 저수준 제어기를 만들지 않는다.

## 원고 교정

1. MultiThreadedExecutor의 별도 callback group은 병렬 실행 기회를 제공한다.
   모든 타이머가 반드시 20ms 안에 실행된다고 보장하지 않는다. CPU-bound Python
   연산의 GIL과 OS 스케줄러 영향이 있으므로 프로세스 분리·bounded worker와
   실제 명령 간격 측정을 함께 구현했다.
2. Reentrant 그룹에 무거운 콜백을 무제한 겹치게 두면 작업이 쌓일 수 있다.
   인지 입력은 빠르게 timestamp를 검사한 후 최신 한 쌍만 큐에 유지한다.
3. Service는 요청/응답 패턴이며 반드시 동기 방식으로 호출할 필요는 없다.
   상태 관리자는 bounded future 대기, 팔 노드는 별도 실행기 스레드가 동작하는
   Reentrant 그룹에서만 서비스/액션 완료를 기다린다.
4. Inactive는 하드웨어 Torque Off가 아니다. 구현은 런타임의 새 명령을 차단한다.
   하위 position controller는 기존 목표를 유지한다.
5. `Pose`만으로는 프레임과 시각을 알 수 없으므로 PickObject 목표를 PoseStamped로
   교정했다. 현재 지원 프레임은 base_link이며 stale/future/비정상 입력을 거부한다.
   서로 다른 프로세스의 시뮬레이션 clock 전달 순서 때문에 최대 50ms 앞선 시각은
   허용하고 그 이상은 거부한다. 이 경계는 별도 회귀 테스트로 검증한다.
6. 50ms ApproximateTimeSynchronizer는 시각이 가까운 메시지를 묶으며 정확한 시점
   보간이나 좌표 변환을 수행하지 않는다. 처리 후에도 300ms 신선도를 재검사한다.
7. 물리 파지·MoveIt이 없는 단계에서 PickObject를 성공 처리하면 잘못된 과제 완료
   판정이 된다. dry_run 목표만 허용하고 완료 시 NOT_IMPLEMENTED/ABORTED 및
   success=false를 반환한다. 취소는 실제 CANCELED 상태로 반환한다.

## 실제 검증

최종 회귀 테스트는 29개 통과, Ch13 세 패키지 빌드는 성공, `colcon test-result`는
18 tests / 0 errors / 0 failures / 0 skipped였다. 명령과 의존성 버전은
evidence/section_13_3/validation.json에 기록했다. 외부 MuJoCo overlay 자체의
upstream unit test는 실행하지 않았으며 Ch13 엔진 통합 시험으로 확인했다.

| 실제 엔진 | 명령 간격 표본 | 중앙값 | 95백분위 | 최대 간격 | 기능/런타임 종료 |
|---|---:|---:|---:|---:|---|
| Gazebo Harmonic | 498 | 23.395ms | 45.806ms | 69.078ms | PASS / PASS |
| MuJoCo | 501 | 19.708ms | 42.213ms | 82.160ms | PASS / PASS |

최대 간격이 20ms를 넘으므로 이 결과를 hard realtime 성공으로 표현하지 않는다.

`Ch13/evidence/section_13_3/{gazebo,mujoco,startup_failure}`에 엔진·런타임 로그와
검증 JSON을 보존한다. 두 엔진에서 동일한 검증기가 실제 ROS API를 호출한다.

- 기동 순서: 팔 configure → 다리 configure → 팔 activate → 팔 안전 자세 측정 →
  다리 activate. 실제 stow 궤적의 상태·오류 코드를 검사한다.
- 200ms 인지 작업 지연 중에도 다리 명령을 수백 회 수신하고 간격 분포를 측정한다.
- PickObject의 실행 요청 거부, stale 목표 거부, 피드백, 중복 목표 거부, 취소,
  dry-run 완료를 물리 파지 실패로 보존하는 동작을 확인한다.
- 2초 오래된 센서 쌍은 처리하지 않으며 STOP 및 Inactive 후에는 새 다리 명령이 없다.
- 엔진 없는 실행은 팔 컨트롤러 부재로 기동이 FAILED가 되고 팔이 Inactive로
  rollback되며 다리 명령이 0회다.
- 두 엔진·실패 시험·빌드를 한 WSL 호스트에서 동시에 실행했을 때 기동 deadline
  초과 또는 샘플 부족이 관측됐다. 이후 잔존 Gazebo 서버도 발견했으므로 CPU 부하만을
  원인으로 분리 입증한 시험은 아니다. parallel_stress_observation.json에 이 한계를
  기록했다. 최종 주기 측정은 잔존 프로세스를 정리한 후 각 엔진을 단독 실행했다.

첫 종료 시험에서 launch와 하위 프로세스에 SIGINT를 동시에 보내 cleanup을 두 번
중단하는 현상이 있었다. 실행기는 launch 부모에만 먼저 SIGINT를 보내고, 런타임은
컨텍스트를 닫기 전에 실행기·작업자를 정리하도록 수정했다. 설치된 Jazzy 실행기가
guard condition을 파괴한 후 worker pool을 join하는 순서에서도 callback 종료 경쟁이
재현됐다. `common.py`의 DrainingExecutor가 worker pool을 먼저 drain하도록 교정한다.
이 한 곳은 rclpy의 private `_executor` 멤버를 사용하므로 ROS 업그레이드 시 반드시
실제 종료 시험을 반복해야 한다. 수정 전 현상은 before_shutdown_fix.json에 보존했다. 최종 결과는
`runtime_shutdown` 항목과 원본 로그에서 확인한다. MuJoCo upstream 통계 스레드의
종료 시 context-invalid 경고는 별도이며 프로세스의 실제 종료 결과도 로그에 남긴다.

후속 MuJoCo 실행에서 기본 KeyboardInterrupt가 `take_message`의 pybind 변환 중
발생해 RuntimeError로 보이는 경우도 재현했다(before_signal_fix.json). SIGINT는
종료 Event만 설정하게 하고, 100ms 이내 executor wait가 반환한 뒤 정리하도록
수정했다. state_manager는 하나의 지속 SingleThreadedExecutor와 서비스 클라이언트
캐시를 사용해 기동 중 노드/클라이언트를 반복해서 실행기에 붙였다 떼지 않는다.

검증 환경의 설치 버전은 rclpy 7.1.12, controller_manager 4.48.1,
gz_ros2_control 1.2.20, message_filters 4.11.17, mujoco_vendor 0.1.0이다.
공식 MuJoCo overlay와 native Python 검증 환경은 작업 중 임시 폴더 소실 후
동일 커밋·MuJoCo 3.3.7로 영속 폴더에 복구했다.

반복 시험에서 launch 부모가 종료된 뒤 남은 Gazebo 서버 자식이 다음 실행의 준비
검사에 응답하는 문제도 발견했다. 실행기는 자신이 새 세션으로 생성한 프로세스
그룹만 종료하고, SIGTERM 뒤에도 남은 자식에는 제한 시간 후 SIGKILL을 적용한다.
기존 사용자 시뮬레이터는 대상으로 삼지 않는다. 해당 재현은
before_process_cleanup_fix.json에 남겼다. 실행 시작에 result.json을 RUNNING으로
초기화하고 예외 시 FAIL로 덮어써 이전 성공 결과가 새 실행 실패를 가리지 않게 했다.

## 자체 리뷰 결과와 제한

- 안전 자세는 13.2의 직립 영점으로, 접힌 운반 자세나 collision-aware planning이 아니다.
- 기동 순서는 런타임 노드의 lifecycle/명령 허용 순서다. 13.2의 하위 ros2_control
  컨트롤러는 이미 active이며 이 절에서 하드웨어 전원을 순차 제어하지 않는다.
- ROS 시간과 수신 후 monotonic 시간을 함께 검사해 clock 정지 시 stale 관절 상태로
  계속 새 명령을 내지 않도록 했다. STOP은 자동 복구하지 않고 명시적 재요청을 요구한다.
- 모든 공유 관절/모드/목표 예약 상태는 Lock으로 보호한다. 목표 예약은 실행 이전에
  수행해 동시에 들어오는 두 액션이 모두 수락되지 않도록 했다.
- 기동 rollback의 컨트롤러 부재 경로는 실행 검증했다. 네트워크 분단, 하드웨어
  전원 차단, planner hang, 긴 학습 정책 안정성은 미검증이다.
- live 센서 TF·YOLO 검출·SLAM·PPO·MoveIt 2·Behavior Tree·실제 파지는 후속 구현이다.
- WSL 일반 스케줄러에서 측정한 결과다. hard realtime, 안정 보행이나 운반 성공을
  주장하지 않는다. 주기 분포의 숫자는 각 result.json을 따른다.

## 참고 근거

- [ROS 2 lifecycle 설계](https://design.ros2.org/articles/node_lifecycle.html)
- [Jazzy rclpy callback groups 소스](https://github.com/ros2/rclpy/blob/jazzy/rclpy/rclpy/callback_groups.py)
- [message_filters Python 구현](https://github.com/ros2/message_filters/blob/jazzy/src/message_filters/__init__.py)
- 설치된 Jazzy rclpy/message_filters API를 직접 검사하고 실제 실행으로 검증했다.
