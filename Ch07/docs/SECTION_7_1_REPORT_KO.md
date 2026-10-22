# SECTION_7_1_REPORT_KO — 로봇 비전의 개요와 실무 적용 분야

> 기준일: 2026-10-20 (KST) · 기준 commit: a318c04a69a003e5c5d5998f077f2b8a8f36a1a5 · 기준 브랜치: main
> 원고: 사용자가 첨부한 「7장. 물체 인식 및 조작」의 7.1절
> 판정: **REVIEWED — 개념 절, 통합 실행 미검증**
> 검증 등급: **STATIC_REVIEW_ONLY** (원격 GitHub 소스 확인 및 명시적 문자열·계약 점검, ROS 2/Gazebo 실행 테스트 아님)

## 1. 목적과 범위
Ch12의 가이드/절별 보고서 분리 원칙을 따라 **구현된 사실과 권장 수정, 실측 결과와 예상 결과**를 구분한다. 원고 예시는 본문의 교육 설계 기준이며, 명령어와 실제 코드가 다른 경우에는 저장소를 우선해 판정한다. 이 보고서는 문서/코드 리뷰 결과이며 실제 코드 수정 완료를 뜻하지 않는다.

## 2. 확인한 실제 소스
- [Ch07/ros2_ws/src/vision_basics/package.xml](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/package.xml)
- [Ch07/ros2_ws/src/vision_basics/setup.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/setup.py)
- [Ch07/ros2_ws/src/vision_basics/vision_basics/object_detector.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/vision_basics/object_detector.py)
- [Ch07/ros2_ws/src/vision_basics/vision_basics/mission_controller.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/vision_basics/mission_controller.py)

## 3. 핵심 발견사항(심각도 기준)
1. **[HIGH] 원고 아키텍처와 구현의 경계 불일치:** 원고 7.1은 RGB-D → TF2 → MoveIt 2 → 물리 파지까지 한 시스템으로 소개하지만, 확인한 패키지의 노드 실행 등록과 카메라/TF 통합은 완성되어 있지 않다. 교육용 목표 아키텍처를 이미 동작하는 결과로 표현하면 안 된다.
2. **[MEDIUM] 패키지명 불일치:** 본문에는 my_robot_vision, 실제 저장소에는 vision_basics가 있다. 절마다 실제 경로와 명령을 통일해야 한다.
3. **[MEDIUM] 2D와 3D의 개념 분리:** 단안 RGB에서 한 픽셀은 3D 한 점이 아닌 광선이다. RGB-D의 depth 또는 평면 교차 가정과 K, TF가 필요하다. 물체 영역 픽셀 중심의 깊이는 표면점이며 자동으로 파지 중심이 되지 않는다.
4. **[MEDIUM] 시각 기반 서보잉 용어:** 이 장의 제시 파이프라인은 검출→목표 위치 변환→계획 실행에 가깝다. 연속 영상 오차 피드백 제어(IBVS/PBVS)를 구현·측정하지 않고 완성된 visual servoing으로 선언하면 안 된다.

## 4. 수정 권고 및 교육 설계
- 도서 첫 페이지에 **학습 목표**(좌표·QoS·검출·TF·계획·파지)와 **현재 구현 상태**(준비/차단/미검증)를 별도 표로 제시한다.
- 핵심 인터페이스 계약을 표준화한다: /camera/image_raw(Image), /camera/camera_info(CameraInfo), /camera/depth/image_raw(Image), /camera/target_pixel(PointStamped, 픽셀/면적), /robot/target_position(PointStamped, m), MoveIt action과 그리퍼 action.
- 독자에게 단위(픽셀/㎡ 아닌 pixel²/m), frame_id, stamp, QoS, 실습과 실제 안전 조건을 구분하도록 유도한다.
- 후속 절 7.2~7.7의 독립 실습을 검증한 후 종합 시나리오를 소개한다.

## 5. 테스트·Evidence
- **수행:** GitHub 메인 브랜치의 package.xml/setup.py/object_detector.py/mission_controller.py 정적 대조.
- **확인:** 패키지는 vision_basics이고, 아키텍처의 인식 결과와 미션 소비 계약이 아직 연결되지 않음.
- **미수행:** ROS 노드 실행, 실제 영상 수신, Gazebo 물리 검증(현재 환경에 ROS/Gazebo 런타임 없음).

### 재검증 체크리스트
- [ ] source 환경 충돌 제거 및 colcon build로 해당 패키지 설치 확인
- [ ] ros2 pkg executables/launch, 직접 의존성, 토픽 타입/QoS/네임스페이스 검사
- [ ] 관련 절의 정상/실패 입력에 대한 단위·정적 회귀 테스트
- [ ] Gazebo Harmonic + ROS 2 Jazzy에서 실제 런치, 로봇 동작/종료 확인
- [ ] 터미널 명령·exit code·토픽/TF/액션·화면/CSV의 원본 Evidence 확보
- [ ] Ch07 단독 overlay에서 실행하고 이전 장 패키지 설치경로 섞임 확인

## 6. PR 판단
**문서 리뷰 PR은 검토 가능, 해당 절 실습이 이미 정상 실행된 것으로 승인 불가.** 실습 가이드의 명령 중 선행 수정 조건이 있는 단계는 수정 후에만 진행한다. 수정·시험을 완료하면 이 파일의 STATIC_REVIEW_ONLY 상태를 실제 결과로 교체해 재심사해야 한다.

관련 문서: [LAB_7_1_GUIDE_KO.md](LAB_7_1_GUIDE_KO.md).
