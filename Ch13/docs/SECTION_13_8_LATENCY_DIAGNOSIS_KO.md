# 13.8 반복 실패 원인과 지연 검증

2026-11-05 KST. 단일 작업자. 개발 중간 기록이며 전체 원고 인수 보고서가 아니다.

## 조사 방식

실패 이름만 보고 같은 원인으로 묶지 않는다. 실제 원본 촬영 시각, 렌더 완료, DDS 최초 수신, 검증 결과 발행, 안전 경계의 판정 시각을 연결한다. 공식 설치 버전의 구현을 우선 확인하고, 다른 버전의 GitHub 사례는 비교 근거로만 사용한다. 실패 로그와 동결 소스는 보존하고 안전 기준을 늘려 성공으로 바꾸지 않는다.

## 이미 구분한 실패 계열

| 계열 | 실제 근거 | 적용과 확인 범위 |
|---|---|---|
| 운반 중 원통 가림 | v2는 파지/접촉 유지 뒤 부분 가림으로 새3D 점 획득 중단 | 운반은 새 원본 RGB-D health와 실제 양 finger 접촉·고정 팔을 요구하는 별도 권한. 정지 조작에는 다시 새3D 점 필수. v10에서 실제 운반/PLACE 진입 확인 |
| 혼합 relay 지연 | v4에서는 새 health가 생산돼도 navigation의 혼합 FIFO에 늦게 반영 | 13.8 opt-in 독립 latest-only health lane. 기본13.6/13.7 유지. v10 실제 정상 귀환 확인; 모든 지연 제거 보증은 아님 |
| 귀환 자세 오류 | v5 goal의z만 설정해 기본w=1 잔류 | 공식 ROS quaternion 패턴으로 네 성분 명시·정규화. v10 실제 정상 yaw와 PLACE 진입 확인 |
| 검출 오류 진단 누락 | v9 결합 frame의 실제 거부는 surface RMS였으나 첫 조각의 높이 부족으로 표시 | 실제 결합 오류 보존. foreground boundary depth bleed만 선별 제거. 원통 높이/RMS/TF 기준 유지. v10 실제 파지 PASS |
| 팔에 붙은 충돌 모델 분리 실패 | v10 ADD parent=tcp/REMOVE parent=link6. 바깥 서비스 성공이어도 attached 잔류 | 공식 MoveIt2.12.4 ID-only REMOVE·GetPlanningScene 사후 검사. 설치 API 재현/수정 확인 PASS. 이후 팔 후퇴의 실제 인수는 별도 |
| 렌더·전송의 일시적 지연 | v11 이동 초기에 source 나이303.330ms, 다음 health 검증이 fault보다4.259ms 늦음 | 아직 원인 분해 중. v12는 render 대기/계산·프로세스 CPU 계측만 추가. 제어·deadline 변경 없음 |

## v11의 판정 시각 연결

UUID408dabfc-fca3-44e9-8087-fafb3984dd14, source v11/db5586b32b1e4947d0dc3026cc2f35b2e8c1fac7bc39c6052ab71cb1f9f92389.

| 경계 | 기존 health의 frame | 다음 frame |
|---|---:|---:|
| 원본 capture wall | 284.016571911 | 284.176818983 |
| render 완료 wall | 284.157893 | 284.293698 |
| publish 완료 wall | 284.159183478 | 284.295161204 |
| health 검증 wall | 284.182517168 | 284.324160962 |

안전 판정은284.319901497wall이다. 기존 source는303.330ms 나이여서300ms 기준을 넘었다. 그때 아직 생산되지 않은 다음 검증 결과를 소급해서 사용하지 않는다. 원본 렌더 기록은 capture→render 완료만 있으므로 대기와 실제 계산 시간을 구분할 수 없다.

종료 후 같은 실제 저장20자세를100회 렌더한 시험은 warmup5개 제외95frame의 render median4.758ms/p95 8.325ms/max27.471ms였다. 실제 GL 장치는Mesa25.2.8/LLVM20.1.2의llvmpipe CPU renderer다. 이 idle 결과를 실제 부하 상태의 지연 상한으로 표현하지 않는다. 새 계측에서는 render 시작과 process CPU를 함께 기록해 판단한다.

## 공식 근거와 채택 판단

- [Jazzy executor 공식 원본](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Executors.rst), [callback group 공식 원본](https://github.com/ros2/ros2_documentation/blob/jazzy/source/How-To-Guides/Using-callback-groups.rst): callback 실행 순서·기본 mutually-exclusive 그룹의 경계를 확인했다. 스레드 수만 바꾸지 않고 실제 경계를 계측한다.
- [rclpy #1223](https://github.com/ros2/rclpy/issues/1223): Iron/FastDDS에서 다중 스레드의 timer 성능 저하를 보고한 비교 사례. 이 Jazzy 문제의 확정 원인이나 수정 완료 사례로 사용하지 않는다.
- [Mesa LLVMpipe](https://docs.mesa3d.org/drivers/llvmpipe.html), [LP_NUM_THREADS](https://docs.mesa3d.org/envvars.html#lp-num-threads): CPU 렌더와 worker 수의 의미를 확인했다. 실제 설치 GL query와 문서 설명을 연결했으며 드라이버/전역 환경은 변경하지 않았다.
- [MoveIt2.12.4 planning_scene.cpp](https://github.com/moveit/moveit2/blob/2.12.4/moveit_core/planning_scene/src/planning_scene.cpp): 잘못된 parent의 REMOVE 거부를 확인했다. 실제 설치 API의 재현·ID-only 사후 검사 결과는 preflight_v11/offline_detach_api_v11.json에 있다.

## 다음 검증

v12의 계측 결과로 대기·렌더 CPU·DDS 수신·검증 중 지연이 집중되는 경계를 특정한다. 같은 실패가 없더라도 한 번의 통과로 반복 강건성을 주장하지 않는다. 연속 파지→운반→내려놓기→팔 후퇴→유지→정상 종료와 원고의3cm/120초 목표를 별도로 판정한다. Level1/2/3 및 고정 설정10회 평가는 아직 미완료다.
