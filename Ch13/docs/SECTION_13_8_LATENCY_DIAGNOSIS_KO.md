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

## v12의 다른 경계: 최초 action 준비

v12는 navigation/정착/find를 통과했지만 첫 warmup arm action 전에MISSION_EXPIRED로 FAIL했다. heartbeat producer의sequence1→2 자체가 약455ms 끊겼다. 새 render 계측은 이때 source 대기 약13~43ms/render wall 약10~40ms였으므로 이를 v11과 같은 카메라 지연이라고 부르지 않는다.

설치rclpy7.1.12 공식 [ActionClient](https://github.com/ros2/rclpy/blob/7.1.12/rclpy/rclpy/action/client.py)와 [type_support](https://github.com/ros2/rclpy/blob/7.1.12/rclpy/rclpy/type_support.py)에서 최초 타입 로딩의 동기 실행을 확인했다. 실제 별도domain136 probe의warmup import16.635ms/arm client98.471ms였다. live455ms의 모든 세부 기여를 이 idle시험만으로 확정하지는 않는다.

[공식 lifecycle 설계](https://design.ros2.org/articles/node_lifecycle.html)와 [Jazzy 실시간 프로그래밍 문서](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Demos/Real-Time-Programming.rst)의 일회 준비와 실행 경로 분리 패턴을 적용했다. 13.8 ready에서warmup 모듈·action3종·MoveIt service4종 타입 지원을 준비하고, 실제 client·goal·cancel 수명은 기존 단일 owner에 둔다. kernel/priority/memory locking/QoS/관측 나이 기준은 변경하지 않는다.

준비 probe는340.085ms를 live권한 이전에 사용했고 이후arm client5.420ms였다. 전체318 PASS/51.06초 후v13 source340/assets94로 동결했다. 실제v13의warmup client 구간은arm15.922ms/gripper11.856ms였고, 기존 실패 지점을 통과해PRE_GRASP를 실행 중이다. 아직 전체 임무 성공으로 판정하지 않는다.

## v13의 검출 거부와 v14의 계약 변경

v13은 최초 팔 준비를 통과했지만 접근 중 표면 검사6회 거부로 전체 FAIL했다. 마지막 frame은 높이79.393mm와 상하 조각의 위치 일관성을 만족했으며, robust 중심은(1.800023,-0.000111)m였다. side 오차q90는0.0998mm이나 소수점이 반경33.590mm로 튀어 전체 RMS1.578mm였다. 기존 이웃 기반 boundary 필터는 이 frame에서0pixel을 제거했다.

같은 계열이 남아 이웃 임계값을 더 조정하지 않았다. [PCL1.15.1 공식 원통 분할](https://github.com/PointCloudLibrary/pcl/blob/pcl-1.15.1/doc/tutorials/content/cylinder_segmentation.rst)의 모델→합의점→재계산 패턴과 기존 SciPy robust 추정을 결합했다. 13.8 새mode는2mm 이내side점95% 이상을 요구하고, 그 집합으로 중심을 재계산한다. 이후에도95% 비율·RMS1.5mm·높이75~105%·side 폭/최소20점을 검사한다. 과거 이웃 필터는 live에서 끈다.

residual_m의 모집단이 전체 점에서 합의점으로 바뀌므로 명시적 검출 계약 변경이다. rawRMS·전체/제외 점수·합의점 비율을 함께 남긴다. v9/v13 실제 거부 영상,25% 깊이 손상,가림,747자세 시야와 기존 소유권/수명 회귀를 포함해322 PASS/54.67초. source 동결과 실제 연속 동작 확인은 별도다. 기본13.6/13.7은 기존 전체점 fit을 유지한다.

## v14의 표시 파일 오류와 v15 수정

v14는 실제 파지 물리 PASS(최소100.460mm/2.18sim초/양 finger 접촉100%) 후 귀환 중 전체 FAIL했다. 원인은 BT timer에서 live_status.json을 교체하던 PermissionError가executor로전파된 것이다. 이로써mission_exception 취소가 발생했고RETURN_GOAL_FAILED가 뒤따랐다. 상태 파일의 마지막CARRY 표시는 최종 판정이 아니며 trial/BT/engine 자료를 함께 확인했다.12 child 정상 종료·worker join·lock free는 확인했다.

[Windows 공식 파일 공유 규칙](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)에 따르면rename도delete공유가필요하다. 새시험파일을Windows reader가DELETE공유없이연상태에서WSL replace를시도해같은PermissionError를실제재현했다. OS권한이나다른프로세스를변경하지않는다.

v15는상태표시파일I/O를한개의owned writer thread로분리한다. pending은하나뿐이고오래대기한표시상태는다음상태로대체한다. 오류·대체수·실제join은telemetry_delivery.json에남긴다. 원래제어·관측·접촉·취소계약은유지한다. 잠금복구/느린writer/한도/join실패·정상종료시험과실제Windows/WSL재현PASS, 전체325 PASS/48.99초. 원고바닥캔의정적위치IK조사에서는0.5~0.7m stand-off 후보를얻었으나6D계획/물리성공증거는아니다. 그확장은연속미션인수후진행한다.
