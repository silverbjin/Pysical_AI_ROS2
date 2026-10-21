# SECTION_7_4_REPORT_KO — OpenCV 기반 물체 인식 알고리즘 구현

> **2026-10-21 후속 수정 안내:** 이 문서는 **2026-10-20 수정 전 코드의 리뷰 기준선**입니다. 최신 코드 수정·원격 정적 테스트 결과는 [SECTION_7_4_FIX_TEST_REPORT_KO.md](SECTION_7_4_FIX_TEST_REPORT_KO.md)를 참고하십시오. 신규 코드의 ROS 빌드·시뮬레이터·물리 파지 성공은 여전히 미검증입니다.

> 기준일: 2026-10-20 (KST) · 기준 commit: a318c04a69a003e5c5d5998f077f2b8a8f36a1a5 · 기준 브랜치: main
> 원고: 사용자가 첨부한 「7장. 물체 인식 및 조작」의 7.4절
> 판정: **BLOCKED — 검출 로직은 존재, 메시지/등록 계약 불일치**
> 검증 등급: **STATIC_REVIEW_ONLY** (원격 GitHub 소스 확인 및 명시적 문자열·계약 점검, ROS 2/Gazebo 실행 테스트 아님)

## 1. 목적과 범위
Ch12의 가이드/절별 보고서 분리 원칙을 따라 **구현된 사실과 권장 수정, 실측 결과와 예상 결과**를 구분한다. 원고 예시는 본문의 교육 설계 기준이며, 명령어와 실제 코드가 다른 경우에는 저장소를 우선해 판정한다. 이 보고서는 문서/코드 리뷰 결과이며 실제 코드 수정 완료를 뜻하지 않는다.

## 2. 확인한 실제 소스
- [Ch07/ros2_ws/src/vision_basics/vision_basics/object_detector.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/vision_basics/object_detector.py)
- [Ch07/ros2_ws/src/vision_basics/setup.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/setup.py)
- [Ch07/ros2_ws/src/vision_basics/package.xml](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/package.xml)

## 3. 핵심 발견사항(심각도 기준)
1. **[HIGH] 원고는 geometry_msgs/Point를 발행한다고 설명하지만 실제 코드는 PointStamped를 사용한다.** frame_id/stamp 보존 측면에서는 개선이나, 7.5 구독자도 PointStamped로 구현해야 한다. 이를 수정 없이 조합하면 ROS 타입 불일치가 발생한다.
2. **[HIGH] 면적 임계값이 다르다:** 원고 >500px², 실제 object_detector.py는 >50px². 저해상도 노이즈가 오검출될 수 있어 threshold별 precision/recall 또는 test mask 비교가 필요하다.
3. **[BLOCKER] object_detector 실행 항목 미등록.** 원고 ros2 run my_robot_vision object_detector는 패키지명 및 등록 모두 맞지 않는다.
4. **[HIGH] 목표 미검출 시 무효/해제 메시지를 보내지 않는다.** 하위 노드가 이전 좌표를 새 목표로 오인할 수 있다. PointStamped.point.z에 area를 넣는 것은 공간 Z(m)가 아닌 픽셀 면적이라는 비표준 의미다.
5. **[MEDIUM] red 이중 Hue 범위, opening/closing, contour max 및 moment 0 분모 방어, 디버그 이미지 header 유지는 좋은 기초 구성이다.** 단일 색·최대 면적을 가장 가까운 물체로 해석하는 원고 설명은 엄밀하지 않다.

## 4. 수정 권고 및 교육 설계
- detector 메시지를 명시적으로 PixelDetection(픽셀좌표/면적/valid/stamp) 또는 PointStamped의 엄격한 계약으로 문서화하고 소비자 타입 일치.
- 파라미터로 면적/H/S/V/커널 값을 노출하고 빨강/오검출/복수/조명 변화 회귀 테스트를 추가한다.
- 미검출·기한 초과 시 fail-closed, 표면 bounding box 크기 대비 안정성 지표를 추가한다.
- 설치 엔트리와 직접 의존성을 추가하고 7.2 영상 연결 후 실제 검출 영상을 남긴다.

## 5. 테스트·Evidence
- **수행:** object_detector.py와 원고의 메시지 타입·면적 임계값·종단 출력 계약을 비교, 정적 진단.
- **확인:** PointStamped vs Point, area>50 vs >500, setup.py 미등록, 미검출 시 무효 신호 없음.
- **미수행:** GPU/Gazebo/실제 카메라 기반 검출률·오검출률 측정.

### 재검증 체크리스트
- [ ] source 환경 충돌 제거 및 colcon build로 해당 패키지 설치 확인
- [ ] ros2 pkg executables/launch, 직접 의존성, 토픽 타입/QoS/네임스페이스 검사
- [ ] 관련 절의 정상/실패 입력에 대한 단위·정적 회귀 테스트
- [ ] Gazebo Harmonic + ROS 2 Jazzy에서 실제 런치, 로봇 동작/종료 확인
- [ ] 터미널 명령·exit code·토픽/TF/액션·화면/CSV의 원본 Evidence 확보
- [ ] Ch07 단독 overlay에서 실행하고 이전 장 패키지 설치경로 섞임 확인

## 6. PR 판단
**문서 리뷰 PR은 검토 가능, 해당 절 실습이 이미 정상 실행된 것으로 승인 불가.** 실습 가이드의 명령 중 선행 수정 조건이 있는 단계는 수정 후에만 진행한다. 수정·시험을 완료하면 이 파일의 STATIC_REVIEW_ONLY 상태를 실제 결과로 교체해 재심사해야 한다.

관련 문서: [LAB_7_4_GUIDE_KO.md](LAB_7_4_GUIDE_KO.md).
