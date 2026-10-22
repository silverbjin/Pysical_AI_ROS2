# SECTION_7_5_REPORT_KO — 2D 픽셀 좌표의 3D 공간 좌표 변환

> 기준일: 2026-10-20 (KST) · 기준 commit: a318c04a69a003e5c5d5998f077f2b8a8f36a1a5 · 기준 브랜치: main
> 원고: 사용자가 첨부한 「7장. 물체 인식 및 조작」의 7.5절
> 판정: **BLOCKED — 요구 변환 노드 경로 미확인**
> 검증 등급: **STATIC_REVIEW_ONLY** (원격 GitHub 소스 확인 및 명시적 문자열·계약 점검, ROS 2/Gazebo 실행 테스트 아님)

## 1. 목적과 범위
Ch12의 가이드/절별 보고서 분리 원칙을 따라 **구현된 사실과 권장 수정, 실측 결과와 예상 결과**를 구분한다. 원고 예시는 본문의 교육 설계 기준이며, 명령어와 실제 코드가 다른 경우에는 저장소를 우선해 판정한다. 이 보고서는 문서/코드 리뷰 결과이며 실제 코드 수정 완료를 뜻하지 않는다.

## 2. 확인한 실제 소스
- [Ch07/ros2_ws/src/vision_basics/vision_basics/object_detector.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/vision_basics/object_detector.py)
- [Ch07/ros2_ws/src/vision_basics/setup.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/setup.py)
- [Ch07/ros2_ws/src/vision_basics/urdf/my_robot.urdf.xacro](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/urdf/my_robot.urdf.xacro)

## 3. 핵심 발견사항(심각도 기준)
1. **[BLOCKER] 원고의 coord_transformer.py는 확인한 Ch07/ros2_ws/src/vision_basics/vision_basics/coord_transformer.py 경로에 없다.** 다른 파일·외부 패키지의 구현 여부는 전체 저장소 트리 조사 전까지 미확인으로 남긴다. setup.py에도 엔트리가 없다.
2. **[HIGH] 원고의 변환기 입력은 Point지만 저장소의 detector는 PointStamped를 발행한다.** 타입을 통일하고 이미지 촬영 시각 stamp를 전달해야 한다.
3. **[BLOCKER] 카메라 optical frame 및 depth sensor가 확인한 로봇 Xacro에 없다.** 실시간 역투영·TF 검증을 할 수 없다.
4. **[HIGH] 원고 코드의 depth가 없을 때 0.5m 고정값 사용은 임의의 3D 위치를 만들어 위험하다.** NaN/Inf/0/범위외/미동기 데이터에 대해 목표 publish를 막는 fail-closed가 필요하다.
5. **[HIGH] lookup_transform 최신 시각(rclpy.time.Time())과 현재 시각 stamp는 촬영 시각과 달라 움직이는 eye-in-hand에서 오차를 만든다.** 이미지·depth·CameraInfo의 시간 및 frame 정렬/TF 유효 시간을 검증한다.
6. **[MEDIUM] 원고의 이론 수식 마지막 동차 좌표는 1로 표기해야 하며, pixel=(u,v), depth=Z, fx/fy>0, 단위가 명확해야 한다.** 단일 픽셀 깊이는 파지 중심점·캔 바닥 중심점과 다르다.

## 4. 수정 권고 및 교육 설계
- PixelDetection/PointStamped 입력, depth 정렬, K 유효성 검사, 실제 optical frame_id를 가진 3D PointStamped 출력 노드를 구현한다.
- base_link TF를 **영상 촬영 시각** 기준으로 조회하며 타임아웃·stale·exception·fail-closed를 구현한다.
- 합성 K/depth의 역투영 테스트, 알려진 정적 3D 기준점 오차, 움직이는 손목 테스트를 분리한다.
- 추정한 표면점과 실제 grasp pose(접근 방향, 물체 높이, TCP offset)를 분리한다.

## 5. 테스트·Evidence
- **수행:** 입력 detector 타입, setup.py, URDF camera frame을 정적으로 대조하고 원고의 투영 공식을 수학적으로 검토.
- **확인:** 명시된 coord_transformer.py 경로 미존재(다른 위치의 구현은 미확인), PointStamped 불일치, 카메라 프레임 부재.
- **미수행:** 실제 depth/TF2 변환, RGB-D 동기화 및 원고 2mm 오차 재현.

### 재검증 체크리스트
- [ ] source 환경 충돌 제거 및 colcon build로 해당 패키지 설치 확인
- [ ] ros2 pkg executables/launch, 직접 의존성, 토픽 타입/QoS/네임스페이스 검사
- [ ] 관련 절의 정상/실패 입력에 대한 단위·정적 회귀 테스트
- [ ] Gazebo Harmonic + ROS 2 Jazzy에서 실제 런치, 로봇 동작/종료 확인
- [ ] 터미널 명령·exit code·토픽/TF/액션·화면/CSV의 원본 Evidence 확보
- [ ] Ch07 단독 overlay에서 실행하고 이전 장 패키지 설치경로 섞임 확인

## 6. PR 판단
**문서 리뷰 PR은 검토 가능, 해당 절 실습이 이미 정상 실행된 것으로 승인 불가.** 실습 가이드의 명령 중 선행 수정 조건이 있는 단계는 수정 후에만 진행한다. 수정·시험을 완료하면 이 파일의 STATIC_REVIEW_ONLY 상태를 실제 결과로 교체해 재심사해야 한다.

관련 문서: [LAB_7_5_GUIDE_KO.md](LAB_7_5_GUIDE_KO.md).
