# 13.4 통합 시각 정보 처리 설계서

작성일: 2026-10-18 (Asia/Seoul)

기반: `feat/ch13-section-13-3`, `df993e86d9b6ad446c058bc3b5a61c59c15495db`.
작업 브랜치: `feat/ch13-section-13-4`.

상태: 사용자가 대화에서 승인한 설계를 문서화했다. 이 문서의 검토·승인 후 상세 구현 계획을 작성한다. 현재 13.4 제품 코드나 실행 성공을 뜻하지 않는다. 구현·테스트·리뷰는 서브에이전트 없이 원 세션에서 직접 수행한다. 13.5는 13.4 결과 인계 이후 재개한다.

## 1. 목적과 승인 범위

팔 끝 RGB-D 카메라의 이미지로 물체를 탐지하고, 촬영 시각의 TF로 안정된 기준 좌표계에 위치를 계산하며, 대상별 필터와 추적 상실 판정을 제공한다. 추가로 명시적으로 활성화한 제한적 시선 추적을 기존 팔 제어권을 통해 실행한다.

독자는 ROS 2와 Python을 배운 학부생·초급 개발자다. 단순 코드 조각보다 설치 후 재현 가능한 Ch13 독립 실습, 실제 엔진 실행, 명확한 실패 판정을 우선한다.

포함 범위:

- Gazebo Harmonic과 MuJoCo 3.3.7의 실제 eye-in-hand RGB-D·CameraInfo 발행.
- Ultralytics YOLOv8 계열의 명시적 로컬 가중치 추론과 Detection2DArray 변환.
- 정합된 depth의 단위·유효성 검사, 강건한 깊이 표본, 3D 역투영.
- 이미지 촬영 시각의 TF 조회, 안정된 odom 프레임의 추적·필터링.
- bounded worker, 지연·추적 상실·clock 정지/역행·TF 실패 처리.
- 기본 OFF인 제한적 시선 추적, 기존 manipulation 소유권과 충돌 방지.
- 테스트 우선 구현, 실제 엔진 검증, 한글 가이드·재사용 명세·리뷰 보고서·evidence, 절 전용 커밋·push 및 원격 SHA 확인.

제외 범위:

- Nav2/자동 보행 접근, PPO 보행 학습·안정성 증명, gait switching.
- MoveIt, 일반 IK·collision-aware 경로 계획, 물리 파지·운반·배치 성공.
- 실제 하드웨어 카메라 보정, rolling-shutter·motion-blur의 완전 보상, 일반 환경의 정확도 보장.

## 2. 기존 사실과 새 구현의 경계

- 13.3 vision_processor는 Image/Odometry의 가까운 timestamp를 짝짓고 지연을 흉내 내는 예제다. YOLO, depth, TF 또는 실제 물체 위치를 계산하지 않는다.
- 13.3 locomotion_node는 STAND/HOLD/STOP만 지원하며 PPO/WALK가 아니다. manipulation_node의 stow는 직립 영점 자세이며 접힌 운반 자세가 아니다. PickObject는 물리 작업이 아닌 dry-run 프로토콜이다.
- 13.3 모델에는 camera_link 형상은 있지만 실습용 RGB-D 센서·camera_optical_frame 계약이 없다.
- 설치된 공식 mujoco_ros2_control 소스 `c261f5552edf124d1000a23fb25b6c07cadeb807`에는 CameraPlugin이 있다. 실제 RGB/32FC1 depth/CameraInfo 발행 코드를 확인했으나 Ch13에 연결한 실행 검증은 아직 하지 않았다.
- 현재 검증용 Python 환경에는 cv2/cv_bridge/vision_msgs/tf2_geometry_msgs가 있고 torch/ultralytics는 없다. 구현 단계에서 별도 의존성 설치와 실제 추론을 검증해야 한다.
- 13.1의 별도 패키지 구조와 파지 결과를 13.3 기반 코드에 임의 병합하거나, 13.4의 선행 성공으로 간주하지 않는다.

## 3. 선택한 구조와 대안

선택은 **13.3 유지 + 독립 integrated_robot_vision 패키지**다. 센서·시각 처리를 제어 프로세스와 분리하고, 모터 소유권은 기존 ros2_control/runtime에 남긴다. 기존 13.3의 timestamp 실습은 기본 런치에서 유지해 회귀 검증할 수 있도록 하고, 13.4 런치에서는 실제 시각 파이프라인을 선택한다.

다른 안:

1. 13.1 구조에 13.3을 다시 합침: 이름·launch·제어 소유권이 다른 두 구조를 재통합해야 하므로 이번 범위를 벗어난다.
2. 녹화 영상/합성 메시지만 처리: 기하 단위 테스트에는 유용하지만 실제 센서·TF·엔진 통합 검증을 대신하지 못한다.

패키지 경계:

```text
Ch13/ros2_ws/src/
  integrated_robot_description/  # optical TF, 센서 설정, 검증 fixture/world
  integrated_robot_interfaces/   # 기존 action/service + TrackedTarget.msg
  integrated_robot_runtime/      # 기존 제어권, 제한적 시선 추적 승인/중단
  integrated_robot_vision/       # detector, RGB-D projection, tracking/filter, launch
Ch13/{tests,scripts,docs,evidence/section_13_4}/
```

시각 수학·입력 계약은 ROS 메시지 변환과 분리한다. 시각 패키지가 Ch05~Ch12의 Python 소스·build/install/log를 import하거나 source하지 않는다. 공식 ROS 및 고정 버전 MuJoCo 플러그인은 명시적 외부 의존성으로 기록한다.

기존 13.1의 ignored 산출물은 보존한다. 13.4는 새 `build13_4/install13_4/log13_4` 경로와 자체 Python 환경을 사용하고 다른 절의 설치를 source하지 않는다. 남아 있는 산출물을 새 소스로 커밋하지 않는다.

## 4. 센서와 프레임 계약

공통 카메라 토픽:

| 토픽 | 타입 | 계약 |
|---|---|---|
| /camera/color/image_raw | sensor_msgs/Image | RGB 또는 BGR, 명시적 encoding |
| /camera/aligned_depth_to_color/image_raw | sensor_msgs/Image | color에 정합된 32FC1 m 또는 16UC1 mm |
| /camera/color/camera_info | sensor_msgs/CameraInfo | color와 같은 해상도·optical frame·보정 모델 |

기본 해상도는 320×240, RGB-D 발행 목표는 15Hz, 추론 기본 상한은 10Hz다. 2026-10-19 사용자 승인으로 명시적 `max_rate_hz` 선택 상한을 15Hz까지 허용한다. 기본값·300ms 안전 기준·팔 5Hz 상한은 유지한다. 실제 달성률과 추론 지연을 기록하며 hard realtime을 보장하지 않는다. RGB·depth는 같은 렌더 snapshot을 사용한다.

프레임:

```text
odom → base_footprint → base_link → arm_* → arm_link_6
                                            → camera_link
                                              → camera_sensor_frame
                                                → camera_optical_frame
```

- 몸체는 +X 전방/+Y 좌측/+Z 상방, optical은 +X 우측/+Y 아래/+Z 전방이다.
- 기존 camera_link의 물리 장착 위치·질량은 유지한다. 가상 센서의 고정 외부 변환을 별도 sensor/optical frame으로 명시한다. 영점 자세의 시선은 base_link 기준 `(cos(π/6), 0, -sin(π/6))` 방향을 목표로 한다. 이를 구현하는 고정 회전은 양 모델에서 동일해야 하며 수치 전개는 구현 계획에서 고정한다.
- MuJoCo 렌더 좌표의 -Z 전방/+Y 상방과 ROS optical의 차이를 명시적으로 변환한다. principal ray와 좌우·상하 표적 시험으로 검증한다.
- robot_state_publisher만 로봇 내부 TF를 소유한다. 엔진별 어댑터 하나만 odom→base_footprint를 발행한다. 13.3에 없는 odometry/자유 베이스 pose 발행은 이번 절에서 실제 엔진 관측으로 연결한다.
- 동일 ROS domain에서는 물리 엔진·clock 소유자가 하나뿐이다. 카메라를 위해 두 번째 물리 엔진이나 가짜 이동 TF를 실행하지 않는다.

Gazebo는 실제 RGB-D sensor와 GZ_TO_ROS 관측 브리지를 사용한다. MuJoCo는 기존 물리 엔진에 CameraPlugin을 설정해 같은 mjData 상태의 snapshot을 렌더한다. 영상 발행·광학 변환·엔진 pose의 시각 정합을 따로 확인한다. 렌더 실패를 합성 영상으로 조용히 대체하지 않는다.

## 5. 탐지·깊이·좌표 변환

### 탐지

별도 탐지 프로세스는 최신 프레임 한 개만 대기 큐에 유지한다. 원본 header를 보존한 vision_msgs/Detection2DArray를 발행하며 class_id, score, bbox를 변환한다. 추론 완료 시각으로 촬영 시각을 덮어쓰지 않는다.

기본 backend는 yolo이며 가중치 경로가 필수다. 파일 부재·모델 오류는 명시적 비준비/실패로 처리하고 색상 검출로 자동 전환하지 않는다. 설치 버전·모델/시험 이미지 출처·라이선스·SHA-256을 기록하고 노드 기동 시 자동 다운로드하지 않는다. 실제 가중치 추론이 실행되지 않으면 YOLO 검증을 미검증/실패로 남긴다.

실제 엔진 기하 시험을 위해 `color_fixture` backend를 별도 명시적 옵션으로 제공한다. 이는 붉은 fixture의 결정적 픽셀 검출용이며 YOLO의 성능이나 성공으로 집계하지 않는다. pretrained COCO 모델이 단순 cube를 인식한다고 가정하지 않는다. YOLO 단독 고정 이미지 추론과 엔진 RGB-D→3D 기하 검증, YOLO 엔진 end-to-end 결과를 각각 기록한다.

### 정합과 깊이

- detection의 촬영 시각에 해당하는 RGB-D·CameraInfo를 bounded cache에서 찾는다. 허용 RGB-depth skew 기본 30ms, 입력 최대 ROS age 300ms다. CameraInfo는 같은 calibration ID/해상도/frame이며 최대 age 1s여야 한다.
- 16UC1은 0.001 배로 m로 변환하고 32FC1은 m로 해석한다. 0/음수/NaN/Inf/0.10m 미만/5m 초과는 제외한다. 범위는 파라미터로 노출하되 유효성 검사한다.
- bbox 중심의 내부 5×5 패치에서 유효 depth의 median을 사용한다. 최소 5개 유효 표본이 없으면 위치를 만들지 않는다. bbox 범위를 벗어나는 패치는 자르고, 배경과 섞인 급격한 depth 불연속은 분산/MAD 기준으로 거부한다.
- fx/fy>0, 유한 K, 해상도, stride, endianness, encoding, frame, ROI 및 distortion 전제를 검사한다. 기본은 정류·정합된 입력이다. 보정되지 않은 왜곡 영상이나 color에 정합되지 않은 depth에 같은 K를 사용하는 것을 허용하지 않는다.
- `X=(u-cx)d/fx`, `Y=(v-cy)d/fy`, `Z=d`로 optical 좌표를 구한다. 이 점은 가시 표면의 표본이지 물체 중심/파지점/물체 자세를 보장하지 않는다.

### 시간 기반 TF

검출 header의 시각을 rclpy Time으로 명시적으로 변환하고, 그 시각의 optical→odom TF를 조회한다. 0 timestamp를 latest 조회로 오인하지 않도록 거부한다. TF 대기는 최대 100ms이며 기다리는 동안 제어 루프를 막지 않는다.

Lookup/Connectivity/Extrapolation/Timeout 실패 시 최신 TF로 fallback하지 않는다. 시각·frame·depth가 유효한 관측만 후속 필터에 넣는다. 과거 base_link 좌표는 현재 몸체 좌표와 다르므로 안정된 odom 프레임에서 필터링한다. 이후 현재 몸체 기준 목표가 필요하면 odom의 목표를 별도의 현재 시각 변환으로 옮겨야 하며, 촬영 시각의 base 좌표를 그대로 현재 목표로 재사용하지 않는다.

큐 대기·추론·TF 대기가 끝난 뒤에도 입력 최대 age와 epoch를 다시 검사한다. 대기 시작 때 유효했다는 이유로 이미 만료된 결과를 발행하지 않는다.

TF 조회가 성공해도 카메라 보정·표본·시간 오차가 남는다. 원고의 “정확한 절대 위치/완벽한 보정” 표현은 오차를 측정한 제한적 추정으로 교정한다.

## 6. 추적·필터·유효성 메시지

시각 노드는 `/vision/detections`를 발행하고 `/vision/target_raw`, `/vision/target_filtered`에 PointStamped를, `/vision/tracked_target`에 새 TrackedTarget을 발행한다.

TrackedTarget 계약은 다음을 포함한다.

- header: 위치 기준 frame=odom, stamp=촬영 시각.
- source_header: 원본 optical frame와 촬영 시각, processed_at: 처리 완료 ROS 시각.
- track_id, class_id, score, position, covariance[9], valid, status.
- status는 TRACKED/LOST/INVALID/TF_UNAVAILABLE/RESET 중 하나다. covariance는 표본 기반 근사이며 보정된 통계 신뢰도라고 주장하지 않는다.

동일 class 내 bbox IoU와 3D 거리 gate로 이전 대상을 연결한다. 최소 confidence 기본 0.5, association 최대 거리 0.20m, 추적 TTL 300ms를 사용한다. 식별이 모호하면 제어용 target을 유효 처리하지 않는다. 다른 물체로 전환할 때 기존 필터 상태를 재사용하지 않는다.

필터는 odom에서 대상별 LPF를 수행한다. 기본 time constant 0.20s, `alpha=1-exp(-dt/tau)`로 프레임 간격을 반영한다. 원고의 고정 alpha 방식은 비교 실습 옵션으로 제공하고 0<alpha≤1을 검사한다. outlier는 갱신하지 않으며, time 역행·frame/calibration 변경·track 변경·TTL 초과 시 reset한다. 필터링으로 motion blur가 복구되거나 이동 물체의 지연이 사라진다고 주장하지 않는다.

추적 상실 후 과거 목표를 새 stamp로 계속 발행하지 않는다. invalid 상태 메시지에는 마지막 관측 시각을 보존하며, raw/filtered 유효 위치 발행은 중단한다. ROS age뿐 아니라 monotonic 수신/작업 시간 watchdog도 사용해 simulation clock 정지 시 유효 상태를 무한 유지하지 않는다.

## 7. 제한적 시선 추적과 제어권

기본 launch는 관측만 하며 `tracking_enabled=false`다. 사람의 명시적 활성화 없이 팔/다리 명령을 새로 만들지 않는다.

시각 노드는 모터/trajectory controller에 직접 발행하지 않는다. 새 `/manipulation_node/set_visual_tracking` SetBool 서비스로 활성화 의도를 전달하고, 기존 manipulation_node가 팔 trajectory action client의 유일한 런타임 소유자로서 요청을 검증한다.

- 최초 활성화에는 lifecycle Active, fresh joint state, 다리 STAND/HOLD 또는 STOP의 기립 상태, 유효한 target, 비어 있는 팔 작업 예약이 필요하다. WALK는 기존 구현에 없으므로 허용하지 않는다.
- 이번 추적은 arm_joint_1/arm_joint_5 두 축의 작은 보정만 대상으로 하며 영점 대비 각 ±0.04rad, 속도 0.10rad/s 이하, 명령 상한 5Hz로 제한한다. 13.3의 영점 안전 범위 안에서 수행하는 국소 실험이다. 큰 회전·임의 시선 도달을 보장하지 않는다.
- 두 축의 국소 projection Jacobian을 모델 기반으로 계산하고 principal ray/finite-difference 시험으로 부호와 조건수를 검증한다. singular/나쁜 조건수, 비가시 표적 또는 한계 도달은 정지·상태 보고로 처리한다.
- 하나의 팔 명령만 outstanding으로 허용한다. 이전 trajectory의 결과 또는 취소 확인 전에 새 작업을 겹치지 않는다. stow/PickObject/추적은 같은 예약 상태에서 상호 배제한다. 외부 trajectory 생산자가 발견되면 추적을 중단한다.
- target/depth/TF/joint 상실, 300ms watchdog, lifecycle 전이, clock 역행, operator disable 시 outstanding 추적을 취소하고 마지막 안전 위치 hold로 전환한다. 자동 재활성화하지 않는다. 이 hold는 Torque Off나 충돌 회피 planner가 아니다.
- 픽셀 중심 오차 감소, 한계 준수, 상실 후 새 trajectory 부재를 측정한다. 목표 위치 발행만으로 시선 추적 성공을 선언하지 않는다.

팔의 장거리 수납·일반 물체 접근·파지는 이 국소 시각 추적과 별개다. 13.5로 인계할 인터페이스는 target의 frame/stamp/valid/TTL이며, 아직 Nav2를 연결하지 않는다.

## 8. 구현·검증 인수 기준

제품 코드는 실패 테스트를 먼저 실행한 뒤 구현한다. 최종 검증은 각 엔진을 단독으로 실행하고, 독립적인 빌드/주기 시험과 무거운 엔진을 동시에 실행하지 않는다. 이전 성공 파일은 새 실행의 성공 근거로 쓰지 않는다.

필수 단위/ROS 경계 시험:

1. optical 축과 principal ray, 이름 기반 관절 정렬, 카메라 외부 변환의 URDF/MJCF 일치.
2. 16UC1/32FC1, 잘못된 encoding/stride/shape/K/왜곡/미정합, 0/NaN/Inf/경계 밖 depth와 픽셀, 강건한 패치 추출.
3. 원본 header 유지, 150ms 처리 지연에서 촬영 시각 TF 사용, 최신 TF 대체 금지, TF 부재/분단/버퍼 범위 실패.
4. RGB-depth skew, stale/future/out-of-order, clock 정지/역행, 작업 큐 상한과 오래된 결과 폐기.
5. track ID 전환·재등장·모호한 후보·TTL·outlier·LPF reset와 지연.
6. 시선 추적 기본 OFF, 다른 팔 작업과 배타성, 관절/속도 한계, 센서 상실·disable·lifecycle 종료 후 새 명령 부재.
7. 예외·누락 검사·미완료·오래된 result.json이 PASS가 되지 않는 검증기.

실제 실행 기준:

- Ch13의 4개 ROS 패키지를 앞 장 overlay 없이 빌드하고 전체·colcon 테스트를 실행한다.
- 실제 Gazebo 및 MuJoCo에서 RGB/depth/CameraInfo/TF/joint/clock를 관찰하고 각 frame의 단일 소유권·종료·잔존 프로세스를 확인한다.
- 알려진 fixture 표면에 대한 deterministic detector의 3D 오차를 측정한다. 정적 RMS 위치 오차 ≤0.03m, 150ms 지연과 작은 실제 팔 진동을 준 시험의 historical-TF RMS ≤0.05m를 목표로 한다. 표적 중심과 가시 표면의 차이를 오차에 숨기지 않는다.
- 실제 YOLO 가중치로 고정 시험 이미지 추론을 수행하고 bbox/class/confidence와 시간을 남긴다. 엔진 영상에서도 YOLO를 실행해 검출률·3D 유효 관측 수를 별도 기록한다. 검출 실패를 HSV 결과로 대체하지 않는다.
- 별도로 활성화한 국소 추적은 대상이 보이고 한계 안에 있는 fixture에서 5초 이상 평가한다. 초기 대비 중앙 pixel error의 중앙값 20% 이상 감소와 명령 한계를 함께 확인한다. 조건 밖 표적은 안전한 거부로 평가하되 성공 추적 수에 포함하지 않는다.
- 영상/상태를 끊는 음성 시험에서 300ms watchdog 및 처리/전달 지연 여유 200ms 이내 새 추적 명령 중단을 확인한다.
- RGB-D 기하, YOLO 단독 추론, YOLO 엔진 end-to-end, 팔 추적, 기존 13.2/13.3 회귀를 각각 PASS/FAIL/UNVERIFIED로 보고한다. 필요한 항목 실패·미검증 시 전체를 PARTIAL 또는 FAIL로 남기고 “13.4 완성”으로 쓰지 않는다.

이 수치는 검증할 요구값이지 이미 달성한 결과가 아니다. 물리적으로 달성하지 못한 수치를 테스트 허용치만 바꿔 숨기지 않는다. 제약을 발견하면 근거와 변경 이유를 기록하고 범위가 달라지면 사용자에게 확인한다.

## 9. 문서·evidence·인계

Ch13/docs에 단계별 LAB_13_4_GUIDE_KO.md, 재사용 명세 갱신, SECTION_13_4_REPORT_KO.md를 남긴다. Ch07 색상 검출 코드를 참고/복사하면 원본 commit/path/license/Git-blob SHA-256과 새 경로·수정 이유를 기록한다. draft/error/backup 및 이전 장 설치 산출물을 실행 경로에 넣지 않는다.

evidence/section_13_4에는 환경/의존성·모델·시험 이미지 해시, RED/GREEN·빌드·전체 테스트 로그, 원본 RGB/depth·annotated frame, 시각/TF/위치 오차·추적/주기 표본, 의도한 실패, 종료 결과와 기계 판독 summary를 보존한다. 실패와 성공은 다른 경로에 남긴다. 검증 코드 SHA와 당시 dirty 경로를 기록하고 최종 push SHA는 별도로 대조한다.

13.4 종료 시 구현 범위·미검증 항목·전체 결과와 원격 SHA를 인계한다. 이어 13.5를 별도 브랜치에서 재개하되, valid target 계약을 소비한다는 것과 실제 학습 보행/도착 능력이 있다는 것을 구분한다. 13.5 코드는 이 설계 승인만으로 먼저 구현하지 않는다.

## 10. 설계 근거

- ROS REP-103: https://raw.githubusercontent.com/ros-infrastructure/rep/master/rep-0103.rst
- Ultralytics Predict API: https://docs.ultralytics.com/modes/predict/
- 로컬 ROS Jazzy vision_msgs/cv_bridge/tf2 API와 고정 커밋의 CameraPlugin 소스를 직접 확인했다. 구현 시 설치된 실제 API와 엔진 동작으로 재검증한다.
- 원고의 과거 TF는 시각 정합 원칙으로 채택하지만 “이동 중 항상 정확한 절대 위치”, “필터만으로 보행 진동 해결”, “시선 추적만으로 물리 파지 준비 완료” 주장은 완료 기준으로 채택하지 않는다.

## 11. 자체 설계 검토

- 기존 사실·제안·미검증 상태를 분리했으며 placeholder로 구현 결정을 미루지 않았다.
- 모든 새 모터 명령은 기존 팔 소유권을 거치고 다리 WALK를 요구하지 않는다.
- local 작은 추적과 일반 visual servo/navigation/grasp의 경계를 고정했다.
- 촬영 시각 TF/안정 프레임 필터/최신 한 프레임 큐/clock reset 정책이 서로 충돌하지 않는다.
- 실제 YOLO와 deterministic fixture 결과를 분리해 검증 누락이나 false PASS를 막는다.
- 다음 단계는 이 문서의 사용자 검토·승인 후 상세 구현 계획 작성이다. 실행 방법은 이미 사용자가 선택한 네이티브 모드를 유지한다.
