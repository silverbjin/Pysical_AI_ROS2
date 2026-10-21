# SECTION_7_4_FIX_TEST_REPORT_KO — 물체 검출 파라미터와 픽셀 계약 정리

> 작성일: **2026-10-21 (KST)** · 대상: **feat/ch07-section-7-4** · 저장소: [silverbjin/Pysical_AI_ROS2](https://github.com/silverbjin/Pysical_AI_ROS2)
> 리뷰 기준: `Ch07/docs/SECTION_7_4_REPORT_KO.md` (2026-10-20, base a318c04a69a003e5c5d5998f077f2b8a8f36a1a5)
> 권한: 코드 수정·정적 테스트·동일 원격 브랜치 Push / **main 수정 및 PR 생성 없음**
> 판정: **STATIC_CONTRACT_PASS / ROS_BUILD_NOT_RUN / RUNTIME_NOT_RUN / TASK_NOT_RUN**

## 1. 코드 수정 내역

1. min_contour_area=500.0 pixel² 파라미터 및 양수 검사
2. 검출 조건을 면적 파라미터 기준으로 전환
3. PointStamped z는 거리(m)가 아닌 pixel² 면적임을 명시
4. 미검출 시 옛 좌표를 재발행하지 않음; 소비자 TTL 의무

**공통 변경:** 모든 7.1~7.7 절 브랜치는 `vision_basics/setup.py`에 이미 존재하는 5개 실행 엔트리와 `package.xml`의 직접 의존성 목록을 반영함. 단, 신규 `coord_transformer` 엔트리는 7.5절 브랜치에서만 등록. 공통 파일은 브랜치 간 중복 변경이므로 PR 순차 병합 시 충돌 여부 확인.

## 2. 실제 변경 소스 추적

| 경로 | 근거 |
|---|---|
| `Ch07/ros2_ws/src/vision_basics/vision_basics/object_detector.py` | [해당 브랜치 파일](https://github.com/silverbjin/Pysical_AI_ROS2/blob/feat/ch07-section-7-4/Ch07/ros2_ws/src/vision_basics/vision_basics/object_detector.py) |
| `Ch07/ros2_ws/src/vision_basics/test/test_section_7_4_static.py` | [정적 회귀 테스트](https://github.com/silverbjin/Pysical_AI_ROS2/blob/feat/ch07-section-7-4/Ch07/ros2_ws/src/vision_basics/test/test_section_7_4_static.py) |
| `Ch07/ros2_ws/src/vision_basics/setup.py`, `Ch07/ros2_ws/src/vision_basics/package.xml` | [setup](https://github.com/silverbjin/Pysical_AI_ROS2/blob/feat/ch07-section-7-4/Ch07/ros2_ws/src/vision_basics/setup.py) / [manifest](https://github.com/silverbjin/Pysical_AI_ROS2/blob/feat/ch07-section-7-4/Ch07/ros2_ws/src/vision_basics/package.xml) |

## 3. 수정 후 실제 수행한 테스트 결과

| 검증 항목 | 실제 검사 | 결과 |
|---|---|---|
| 원격 GitHub 파일 직접 읽기 | feat/ch07-section-7-4의 변경된 blob를 재조회하여 문자열/인터페이스/보호 조건 비교 | **PASS** |
| ROS 미사용 정적 계약 검사 | 이 절의 진입점·파일 존재·핵심 로직·메시지 타입·가드에 대한 **6개 assertion** 실행 | **6/6 PASS** |
| 저장소 내 회귀 테스트 추가 | `test/test_section_7_4_static.py`를 원격 브랜치에 추가 | **작성·Push 완료, 저장소 checkout에서 pytest 실행은 NOT_RUN** |

| ROS 2 Jazzy `colcon build` | 현재 도구 실행 환경에 ROS 2가 설치되지 않음 | **NOT_RUN** |
| Gazebo Harmonic · MoveIt 2 · 로봇 제어 | 실측 로그·실행 Evidence 없음 | **NOT_RUN** |
| 물체 물리적 파지 및 E2E Task | 완성도·안전 조건의 실기능 확인 불가 | **NOT_RUN** |

**검증 등급 주의:** 정적 문자열 계약 검사는 Python 컴파일, import, DDS QoS 호환, Gazebo 실행 또는 물리적 성공을 입증하지 않는다. 7.5의 로컬 계산 테스트는 신규 순수 수학 함수의 **동일 로직 복사본**에서 수행했으며 원격 GitHub checkout에서의 재실행은 필요하다.

## 4. 재현 명령(사용자 환경 실행 필요)

```bash
# Ch07 전용 터미널에서, 기존 장의 overlay 환경과 충돌하지 않도록 주의
cd Ch07/ros2_ws
source /opt/ros/jazzy/setup.bash
python3 -m compileall -q src/vision_basics/vision_basics src/vision_basics/launch src/vision_basics/test
python3 -m pytest -q src/vision_basics/test/test_section_7_4_static.py

colcon build --packages-select vision_basics --symlink-install
source install/setup.bash
ros2 pkg executables vision_basics
```

위 명령은 **실행 지침**이며 이 보고서에서 `colcon`·ROS 결과를 PASS로 표기하지 않는다.

## 5. 남은 위험·승인 기준

- **미완료/차단:** 검출 precision/recall, 영상별 검출률, 색상 조명 변화 및 ROS 변환 성능 미검증.
- Python AST/회귀 테스트를 실제 checkout에서 재실행하고 ROS2 노드 시작→토픽/TF/액션 확인→Gazebo 물리 결과 순으로 별도 검증한다.
- `main` 직접 변경·PR 생성/병합 없음. 동일 브랜치에서 코드·테스트·본 보고서를 보존한다.
- 해당 절 이전 리뷰 문서는 **수정 전 기준선**으로 보존한다.

**최종 판정: 코드 수정과 정적 계약 테스트 수행 완료; ROS 빌드·실행·태스크 성공 승인은 보류.**
