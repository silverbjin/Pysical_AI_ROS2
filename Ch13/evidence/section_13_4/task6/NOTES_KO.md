# Task 6: 국소 시선 추적과 팔 소유권

기반 커밋: `a7229d205103b9239dfe45a3ed87199f8e5ea96c`. 이 디렉터리는
Task 6 구현 중의 수정 작업트리를 검증한 원본 기록이다. 최종 커밋 SHA와
별개의 실행 시점 코드라는 점에 주의한다. 다음 Task의 최종 검증이 이를 대체한다.

## 테스트

- `red.txt`: servo/guard 미구현 수집 실패 → `math-guard-green.txt`: 25개 통과.
  URDF FK의 화면 Jacobian을 MuJoCo 카메라 좌표의 독립 수치 미분과 대조했다.
- `owner-red.txt` → `owner-green.txt`: 전송 경계 future를 이용한 4개 검사.
  예약 전에 UUID 등록, 늦은 수락의 즉시 취소, 취소 응답만으로 예약 해제 금지,
  terminal 결과 지연 시 fault 유지, 명시적 복구를 확인했다.
- `runtime-red.txt` → `runtime-negative.txt`: 실제 ROS 서비스/액션 경계 검사.
  시험용 ActionServer이며 물리 엔진 시험을 대신하지 않는다. OFF, 미준비 거부,
  stow/Pick 배타성, operator/loss/lifecycle/외부 trajectory 생산자 취소를 확인했다.
- `rejected-red.txt`: 실패 액션 후 재시도하는 결함 → 실패 시 OFF로 수정.
- `model-red.txt`: 잘못된 XML이 콜백 밖으로 예외 발생 → 비준비 상태로 거부.
- `shutdown-red.txt`: 종료 전 취소 hook 부재. 함께 발견한 시험 실행기의
  spin-thread/종료 경쟁도 수정했다. 제품 실행기는 spin 종료 후 drain 순서를 유지한다.
- 최종 `shutdown-full-green.txt`: **169 passed in 33.25s**.
  `build.txt`의 네 패키지 빌드와 이후 runtime 재빌드 결과는 별도 로그다.

## 실제 엔진

`probe_tracking_13_4.py`는 명시적으로 `color_fixture`를 사용한다. 실제 RGB-D에서
계산한 위치만 소비하고, 가짜 이동 TF나 물체 pose를 탐지 결과로 주입하지 않는다.
기본 OFF의 tracking-goal 수, 한 번의 명시적 enable, 실제 액션, pending 중 disable,
terminal 결과, 후속 goal 부재, 예약 해제, 종료를 검사한다.

- `tracking-mujoco`: **FAIL**. 첫 실행에서 target_fresh가 false여서 enable 거부.
  LOST/INVALID와 valid 표본이 교차했다. 안전 TTL 0.3s는 늘리지 않았다.
  또한 ros2 run 래퍼에만 SIGINT를 보낸 검증기 때문에 5개 자체 그룹을 강제로 정리했다.
  잔존 live PID는 없지만 정상 종료로 계산하지 않는다.
- `tracking-mujoco-replay`: **PASS**. 고정 대기 대신 신선한 실제 표본을 기다리고
  한 번만 enable했다. probe가 설치된 실행 파일을 직접 소유하여 신호를 전달한다.
  컨트롤러에서 추적 UUID의 EXECUTING → CANCELING → CANCELED(5)를 관찰했다.
  모든 자체 프로세스 returncode 0, forced_cleanup=false, residual_live_pids=[].
- `tracking-gazebo`: **PASS**. 동일한 8개 소유권/취소 검사 및 정상 종료.
  Gazebo server stop 응답은 result.json에 별도 기록한다.
- `legacy-mujoco`: 기존 13.3 기능 회귀 **PASS**. measured stow/기립 시동,
  dry-run 취소·중복 거부·실패 전파와 5개 런타임의 정상 종료를 확인했다.
  명목 50Hz에 대해 p95 주기 약 0.040s, 최대 약 0.087s로 hard realtime은 아니다.
- `legacy-gazebo`: 종료 hook을 포함한 런타임 재빌드 후 기존 13.3 기능 회귀와
  runtime_shutdown **PASS**. 원본 결과와 종료 로그를 보존했다.

## 범위와 남은 검증

이 시험은 짧은 국소 액션/취소 smoke test다. **5초 추적의 픽셀 오차 감소,
150ms 지연+실제 카메라 진동의 3D 오차, YOLO 엔진 인식 성공을 뜻하지 않는다.**
물리 파지, MoveIt, PPO 보행, Nav2는 구현/검증하지 않았다.

런타임은 기존 영점 안전 범위 안의 두 축(q1/q5)만 ±0.04rad로 보정한다.
명령 간격 하한 0.2s, horizon 0.2s, 수학적 목표 증분 최대 0.02rad다.
다른 네 관절은 활성화 때의 안전 측정값으로 고정한다. 이 한계가 물리적
충돌 회피나 실시간 보장을 제공하지는 않는다.

추적 전체 세션이 팔을 예약하고, 한 goal만 outstanding이다. 취소 ACK만으로
예약을 풀지 않고 terminal 결과까지 유지한다. 0.5s 취소 결과 제한 초과는
fault이며, 늦은 결과 후에도 명시적 recover_arm_ownership이 필요하다.
이는 Torque Off가 아니며 자동 stow/자동 재활성화하지 않는다.

확인된 후속 문제: MuJoCo의 vision_enabled=false에서 vendor 자동 카메라 등록이
새 eye_in_hand까지 5Hz 렌더한다. 기존 기능 회귀 통과와 별개로 기본 카메라 동작이
완전히 보존된 것은 아니므로 Task 7에서 명시적 legacy 설정과 재검증이 필요하다.
