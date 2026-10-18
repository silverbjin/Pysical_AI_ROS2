# 13.2 구현·리뷰 보고서

## 결론

13.2의 통합 모델 패키지를 `Ch13/ros2_ws/src/integrated_robot_description`에 독립 구성했다. Xacro/URDF, RViz launch, Gazebo Harmonic, MuJoCo MJCF와 공식 `mujoco_ros2_control/MujocoSystemInterface`, 테스트와 측정 스크립트를 포함한다. Ch05~Ch12 파일은 수정하지 않았다.

## 검증 완료

- 단일 TF 트리: `base_footprint` 루트에서 4개 다리, `base_link -> arm_mount`의 6DoF 팔, 그리퍼, LiDAR와 손목 카메라 프레임이 연결된다.
- 관절 매핑: URDF와 MJCF의 20개 가동 관절 이름·축·제한이 일치한다.
- 물리 정보: 모든 URDF 링크에 양의 질량과 대각 관성, 단순화된 충돌 형상이 있다.
- backend 선택: 한 번의 Xacro 확장에서 mock, Gazebo, MuJoCo 중 정확히 한 하드웨어 플러그인만 생성된다.
- 단일 명령 소유권: 다리 12개는 `leg_position_controller`, 팔 6개는 `arm_trajectory_controller`, 그리퍼 2개는 `gripper_position_controller`만 소유한다. `joint_state_broadcaster`는 상태만 게시한다.
- Gazebo: 20개 관절 상태, 네 컨트롤러 `active`, 팔 응답 0.076 rad, 본체 높이 약 0.459 m와 거의 0인 roll/pitch를 실제 측정했다.
- MuJoCo 네이티브: 3.3.7에서 2,000 스텝 동안 유한 상태, 마지막 500 스텝 높이 약 0.451 m, 기울기 0.006 rad 미만을 확인했다.
- MuJoCo ROS 통합: 공식 `MujocoSystemInterface`가 20개 액추에이터를 등록했고 네 컨트롤러가 `active`, 팔 응답은 0.086 rad였다.

측정값 원본은 `Ch13/evidence/section_13_2`에 JSON으로 보존했다.

## 원고에서 수정한 핵심 사항

1. 원고의 “18개 관절(다리 12 + 팔 6)”은 그리퍼를 제어하지 않는 경우에만 맞다. 이 구현은 2지 그리퍼를 포함하므로 가동 관절이 20개다.
2. 원고의 MuJoCo 플러그인 이름 `mujoco_ros2_control/MujocoSystem`은 현재 공식 구현과 다르다. 실제 클래스 `mujoco_ros2_control/MujocoSystemInterface`로 교정했다.
3. 다리에 position/velocity/effort 명령을 동시에 노출하지 않았다. Ch12.8의 검증된 경로가 위치 목표이므로, 이 절에서는 모든 관절을 위치 명령으로 통일하고 각 관절의 소유자를 하나로 제한했다.
4. 팔의 장착 부모는 기존 모델의 실제 몸통 프레임인 `base_link`로 통일했다. 원고의 `trunk`를 그대로 사용하면 존재하지 않는 링크를 참조한다.
5. 카메라 링크에 visual뿐 아니라 collision, 질량과 관성을 추가했다. 뒤쪽 `lidar_link`도 포함해 팔과의 초기 간섭 여유를 두었다.
6. Gazebo와 MuJoCo 모두 같은 컨트롤러 설정을 사용한다. URDF와 MJCF 사이 이름·축·제한의 자동 비교 테스트를 추가했다.

## 재현된 실패와 해결

### Gazebo 설정 경로

긴 `/mnt/c/...` 설정 경로에서 Gazebo 플러그인이 컨트롤러 YAML을 읽지 못하는 현상을 재현했다. 내용 해시 기반의 짧은 `/tmp/ch13_2_controllers_*.yaml` 파일로 물질화해 해결했다. 실패와 성공 JSON을 모두 보존했다.

### MuJoCo 컨트롤러 인자

`controller_manager` 4.48.1은 상속할 인자를 거를 때 값 내부에 `robot_description` 문자열이 있으면 그 인자를 제거한다. 따라서 `integrated_robot_description/.../controllers.yaml` 경로가 제거되고 빈 `--params-file`이 남아 컨트롤러 로딩이 실패했다. 동일한 짧은 임시 경로 우회 후 네 컨트롤러가 모두 활성화됐다. 이는 모델/액추에이터 매핑 실패가 아니며, 실제 실패 로그의 요약을 evidence로 남겼다.

## 기존 기능과 미구현 제안

### 현재 구현

- Xacro 기반 모듈 조립과 접두어 규칙
- 관성·충돌·센서 고정 프레임
- Gazebo/MuJoCo 모델과 launch
- 하나의 `ros2_control` 시스템, 20개 위치 명령 인터페이스
- 컨트롤러 소유권, TF, URDF/MJCF 매핑 자동 테스트

### 미구현 제안

- MoveIt 2 구성, SRDF 그룹, planning scene, self-collision matrix
- effort 기반 보행 컨트롤러와 위치 기반 팔 컨트롤러의 혼합 hardware mode switching
- 카메라·LiDAR의 실제 센서 데이터 플러그인
- 물체, 접촉 기반 파지, 부착/해제, 과제 완료 판정과 실패 복구
- Ch12 PPO 정책 이식, 팔 탑재 후 재학습, 장시간 보행 안정성

따라서 “보행하면서 집고 운반한다”는 후속 통합은 미구현이며, 이번 결과는 정지 자세의 모델·제어 인터페이스 통합 성공이다.

## 미검증 및 제한

- 실제 로봇 하드웨어는 미검증이다.
- RViz launch는 문법·패키지 설치 검사를 했지만 화면을 사람이 육안 판정하는 절차는 자동화하지 않았다.
- self-collision은 단순 형상과 초기 자세로 완화했지만 MoveIt 2의 전체 충돌 행렬은 미검증이다.
- PPO 안정성, 외란·경사·적재 보행, 물체 파지 성공률은 미검증이다.
- Gazebo와 MuJoCo는 짧은 구동 검사다. 장시간 수치 안정성이나 실시간 성능 보증이 아니다.
- WSL은 실시간 스케줄 권한이 없어 `SCHED_FIFO` 경고가 발생했다. 기능 검증은 통과했으나 실시간 결정성은 검증하지 않았다.
- KDL의 루트 관성 경고가 남는다. Gazebo에서 루트 보존을 위해 작은 양의 관성을 유지했다.

## 증거 파일

- `gazebo/before_controller_path_fix.json`: Gazebo YAML 경로 실패
- `gazebo/result.json`: Gazebo 실제 성공 측정
- `mujoco/before_controller_path_fix.json`: MuJoCo 빈 `--params-file` 실패
- `mujoco/native_result.json`: 네이티브 MuJoCo 적분 결과
- `mujoco/ros2_control_result.json`: MuJoCo ROS 2 제어 결과
