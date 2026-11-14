# Ch07 §7.7 G04B — 실제 손가락 구동 차단 근거 및 차기 단일 경계 검수

작성일: 2026-11-14 (KST) · 범위: 시뮬레이션 전용 · 판정: **BLOCKED_ACTUATION_REPRODUCIBILITY**

## 적용 범위 / 증거 경계

- 기준 저장소: `silverbjin/Pysical_AI_ROS2`; 부모 [Issue #173](https://github.com/silverbjin/Pysical_AI_ROS2/issues/173).
- 개발 [Draft PR #180](https://github.com/silverbjin/Pysical_AI_ROS2/pull/180)은 **병합 불가**. 구동 차단 상세 [Issue #181](https://github.com/silverbjin/Pysical_AI_ROS2/issues/181).
- 기인수 G00~G04A는 `main`에서 계속 PASS. 원본 카메라·컨트롤러·URDF·수락 시험은 수정하거나 다시 실행하지 않았다.
- 도서의 실제 Pick-and-Place G04B와 동일 물리 세션에서의 RGB-D→파지 G05는 **NOT_RUN / BLOCKED**. Ch10 [Issue #123](https://github.com/silverbjin/Pysical_AI_ROS2/issues/123)은 HOLD.

## 확정된 관측과 미확정 원인을 분리

| 신규 공개 CI | 원본 증거 / 실제 결과 | 판정 |
|---|---|---|
| [#43571761460](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43571761460) | 손목↔18mm 지지대 실제 접촉 8,591건 (X≈.691m, Z≈1.873m). 수동 부착 아님 | RED |
| [#43572257221](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43572257221) | 10mm 지지대, 해당 세션 손목 간섭 0; finger2≈11.4mm, finger1≈0, 양측 접촉 실패 | RED |
| [#43572765627](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43572765627) | **물체·지지대 접근 전**, `joint4≈π/2`, 두 손가락 동시 12mm 명령: finger1=11.405mm, finger2≈0mm; 외부 접촉 0 | RED |
| [#43573273969](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43573273969) | 같은 자세에서 자유 공간의 finger1 단독·finger2 단독·순차 닫힘 7개 시나리오의 실제 관절 도달 모두 PASS. 이후 손목↔10mm 받침대 1,878건 (X≈.695m)으로 물리 접근 중단 | 부분 진단 PASS / G04B RED |
| [#43574030542](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43574030542) | 6mm 중앙 지지대. 자유 공간 finger2 단독 **12mm 명령에 실제 0mm**, JTC error≈11.94mm, Action SUCCEEDED, 접촉 0건. 물체 접근 전 중단 | RED |

최신 독립 다운로드 원본: [Artifact #14105482197](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43574030542/artifacts/14105482197), ZIP SHA256 `c55c2d49b89f50282e00d4076f6ae1957f8e9c9e73e70e383a16d874dc18e6a3`. 원본에는 실제 `/joint_states`, FJT 목표 및 수락 결과, `/gripper_group_controller/controller_state` error, Gazebo Contact sensor, 소유 PGID/종료 로그가 포함된다.

### 판정의 핵심

- **무충돌 영역에서 한쪽 손가락만 이동하지 않는 실제 증거가 있다.** 따라서 지지대 폭·물체 지름 변경으로 전체 문제를 설명하거나 해결했다고 주장할 수 없다.
- 반대로 동일한 기울어진 그리퍼 자세에서 두 손가락을 개별·순차로 실제 구동한 성공 증거도 있다. 이 변화의 정확한 근본 원인이 Gazebo 물리 솔버인지, `gz_ros2_control`의 SDF 관절 매핑인지, 실행 초기화/시점 문제인지는 **미확정**.
- `FollowJointTrajectory` Action `SUCCEEDED`는 양쪽 관절 이동 성공의 충분조건이 아니다. 공식 [JTC Jazzy 문서](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html)는 Goal tolerance로 실제 관절 도달 조건을 정의하며, 매개변수가 미지정이면 기본 설정을 사용한다고 명시한다. G04B는 독립 `JointState`와 양쪽 Gazebo 접촉력을 계속 요구한다.
- 센서 추가는 **생성된 시험용 URDF/SDF에만**, 원본 물리 충돌·마찰·관절·컨트롤러 파일은 불변. 강제 `attach`, `set_pose`, 텔레포트, 하드코딩 PASS 없음.

## 차기 권장 작업 — 검증 루프가 아니라 실패 경계 단일 진단

1. 기존 승인된 G00~G04A 시험 재실행 금지. 최신 RED 원본 보존.
2. **최소 G04B-DIAG**: 원통·지지대 없이 현행 통합 GazeboSimSystem을 쓰고, `joint4≈π/2`의 문제 자세에서 손가락 하나에 12mm FJT 1회. 실제 `/joint_states`, JTC `controller_state.reference/feedback/error`, `ros2 control list_hardware_interfaces`, Gazebo native prismatic joint position/axis 및 controller-manager 로그를 함께 남긴다. 실제 실패가 발생하는 경우에만 원본 SDF Joint axis와 command-interface 매핑을 분석한다.
3. 새 G04B 테스트에만 양쪽 관절에 **명시적인 목표 오차 제한**과 유한한 결과 대기를 사용한다. 다만 이 변경은 실패를 정확히 반환하게 할 뿐, 물리 관절 동작을 고쳤다는 증거는 아니다.
4. 원인이 특정된 후 가장 작은 코드/설정 변경 1건만 비교 검증한다. **실제 두 관절의 위치·방향·충돌 없음이 확인되기 전에는** 재차 원통 접근을 시도하지 않는다.
5. 이어서만 동일 실제 Gazebo 세션에서 양손가락 접촉과 **실제 원통 Z ≥0.05m 상승**, ≥1.3초 홀드 중 위치 안정, 배치 및 릴리스, 소유 프로세스 정상 종료까지 검증한다. 그 후 G05의 실시간 RGB-D→집기 연결을 새 경계로 다룬다.

**STOP RULE:** 독립적으로 확인된 관절 구동 오류가 해결되기 전 전체 G04B 왕복 주행의 반복 금지. 전 단계의 PASS 임의 승격 금지. Ch10 HOLD 유지.
