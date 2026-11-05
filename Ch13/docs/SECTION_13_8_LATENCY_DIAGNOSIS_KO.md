# 13.8 반복 실패 원인과 지연 검증

2026-11-05 KST. 단일 작업자. 개발 중간 기록이며 전체 원고 인수 보고서가 아니다.

이전에 확인한 v15 개발 fixture의 연속 임무와 물리 pick/transport는 실제1회 PASS했다. 같은 engine에서 내려놓기·팔 후퇴·유지·전체 회수까지 끝냈다. 표시 파일 reader-lock3.115초/오류3회도 제어 취소로 전파되지 않았다. 귀환5.02cm/210.484sim초는 원고 목표 미달이며 Level1/2/3·10회 평가와 구분한다.

현재 최신 v20 Level1은 사전 파지 중 원본 관측 나이가300ms를 넘겨 FAIL했다. 형상 검출 거부는 없었고, 문제 프레임은 렌더 계산25.26ms에 비해 촬영부터 렌더 시작까지164.97ms가 걸렸다. 이 구간에는 요청 전 작업과 큐 전달이 함께 포함돼 있어 아직 원인을 단정하지 않는다. 다음은 작은 부품 계측으로 구간을 나누는 작업이며 원본 수명을 늘리지 않는다. 아래 과거 실패별 기록과 최신 조사 결과를 구분한다.

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

## v20 원본 관측 deadline과 v21 계측

v20 UUIDf4dd835b-09b0-4aed-b7ff-9a86b0eebcfb는61.686sim초/158.594726wall초에FAIL했다. 비전2031회수락/거부1회(capture/clock/TF expired),형상거부0회다. 최초원인은OBSERVATION_EXPIRED이며worker/자식12개정상회수·lockfree다. 새시간보정policy/scale1.06295349·선택plan79.656225sim초는실제적용됐지만완료전에중단됐으므로walldeadline해결을입증하지않는다.

최초faultwall181.029897에서사용중인원본capturewall180.701058은328.839ms전이었다. renderer는180.866025에시작해180.891282에끝났다. 같은시점capture_sensor stage는172.623ms/threadCPU87.604ms였고GC사건은없었다. 다음frame은capturewall180.872739/관측계산180.997220으로fault전에계산됐지만engine의최종observation channel처리는180.962708이었다. camerahealth는181.006100에갱신됐다. 25ms renderer계산만으로전체지연을설명하지않는다.

[Python3.12 multiprocessing Queue 설명](https://docs.python.org/3.12/library/multiprocessing.html#pipes-and-queues)과 [설치계열CPython3.12.3 queues.py](https://github.com/python/cpython/blob/v3.12.3/Lib/multiprocessing/queues.py)를확인했다. put은buffer에넣고별도feeder thread가pickle/pipe전송을수행한다. 따라서put반환이worker수신완료를뜻하지않는다. 이설명만으로이번실패가feeder원인이라고확정하지않는다.

v21계측후보는원본capturewall을그대로보존하며실제request_offer_wall과render시작사이시간을별도로기록한다. SensorSuite의scan/TF상태발행/offer비용을분리하고최대256개최근기록과총수를보존한다. ray/TF/offer순서·제어·모델·관측수명은변경하지않는다. API부재2 FAIL/1기존PASS후새계측/실제별도renderer경로3 PASS/6.43초(348 deselected).

공유lock을잡고별도domain136에서저장qpos300자세의센서생산만재구성한22.29wall초probe는276frame/정상camera회수였다. 최근256기록의scan최대3.13ms,TF상태발행10.14ms,pre-offer12.01ms,put반환0.136ms,요청→renderer시작최대1.237ms,render최대9.827ms였다. 실제walking policy/물리/전체ROS부하가없어165ms지연은재현되지않았다. idle최대값을실제deadline보장으로해석하지않는다. 다음은원래vision/relay를붙인짧은probe다. 추측성새튜닝이나긴engine재시도는이자료로대체하지않는다.
원래vision/relay를붙인첫probe는정적map→odom TF누락으로tf_samples0/accepted0이었다. 원본을API_SETUP_FAILURE로분리보존했다. TF를보완한v2는22.731초/277frame/vision221 accepted·거부0,두자식과camera정상회수였다. 원래12토픽목록의recorder와추가상태발행까지붙인63.391초probe는830frame/vision731 accepted·거부0,세자식과camera정상회수였다. 최근256개producer통계의pre-offer최대11.059ms,전체frame의요청→시작최대6.273ms/render최대8.707ms였다. 실제발행되지않는토픽은대상설정만있는fixture이므로실제12토픽임무bag완료로쓰지않는다. 전체physics/policy/Nav2/MoveIt부하는없다. 이결과로QoS나OS설정을추측변경하지않는다.

관련camera/startup/IPC최종21 PASS/24.23초(330 deselected). 최초20 PASS/1 FAIL은기존cadence시험이생성자를건너뛰어latest_camera기본값이없던fixture초기화누락이며,실제부작용없는free생성자를사용하도록보완했다. 제어350회귀는v20이력이고v21에서전체351을실행한것은아니다. v21은실제한사례로전체부하의pre-offer/전달구간을구분할계측동결이다.

## v21 실제 결과와 owner 프로세스 진단

UUID e0b2d5b0-0678-41e0-87c6-c48793781402는 전체 FAIL이다. 바닥 pick PASS(최소104.914mm 상승,2.2sim초 유지,양 finger 접촉100%), 운반2.560m·귀환36.336mm 후 실제 지지 정착/개방/detach까지 진행했다. 정착은6.917wall초로 새20wall gate 안에서 완료했다. RETREAT 중 최초 fault는 wall471.764171/sim189.944의 MISSION_EXPIRED다. worker/자식12개 정상 회수, bag close와 lock free를 확인했다.

마지막 heartbeat8074는 send471.449932/return471.450114, native receipt471.450333/engine process471.458105였다. 다음8075의 send는471.814146으로 **발행 공백364.214ms**다. 두 stamp는 동일한189902000000ns였다. 발행 뒤 전달 지연으로 해석하지 않는다. 같은 시각 camera health와 observation 수신은 계속 갱신됐다. engine의 GC 기록만으로 별도 owner 프로세스의 GC를 배제할 수 없다.

원래 운반 판정은 carry_height만 false이고 나머지7개 true다. 초기 world Z0.145675628m 대비 최소0.123873742m로21.801886mm 하강해20mm 기준을1.801886mm 초과했다. 그때 TCP 상대 위치 변화는 약4.1mm였으므로 몸통의 높이 변화와 물체 미끄러짐을 구분할 후속 분석이 필요하다. 기존 판정/임계값은 보존하며 바닥 여유가 있다는 이유로 PASS로 바꾸지 않는다. 원고3cm/120초 목표도 미달이다.

### 공식 패턴과 작은 저장 자료 실험

[CPython v3.12.3 gc.rst](https://github.com/python/cpython/blob/v3.12.3/Doc/library/gc.rst)의 is_tracked와 callbacks를 읽었다. 문자열 같은 원자 타입과 중첩 container의 GC 추적 차이, 수집 전후 콜백으로 시간을 관측하는 패턴을 사용한다. disable/freeze/threshold 변경은 적용하지 않는다. [rosbag2 0.26.11 recorder.cpp의 create_subscription](https://github.com/ros2/rosbag2/blob/0.26.11/rosbag2_transport/src/rosbag2_transport/recorder.cpp#L694)은 serialized message와 원래 수신/송신 시각을 보존해 writer로 전달한다. 여기서는 C++ recorder를 복제하지 않고, **현재 제어 상태만 파싱하고 과거 기록은 원문으로 보관**하는 원칙을 참고한다. JSON 원문은 DDS serialized buffer와 같지 않으며 zero-copy라고 부르지 않는다.

저장된 실제 status20,417개를 별도 프로세스에서 읽은 비교: 중첩 dict 보관은 최대 RSS308,764KiB/추적 객체236,304개/수동 gen2 GC61.5~64.5ms였다. 원문 문자열 보관은199,492KiB/93,391개/15.8~17.5ms였고 마지막 상태 의미는 같았다. 원본 실험은 preparation의 owner_status_gc_{parsed,raw}_v21.json에 있다. 로봇·발행자·실제 부하가 없는 사후 실험이며64ms만으로 실제364ms 공백을 설명하지 못한다.

Ruling: 13.8 carry_v1 opt-in에서만 과거 status를 원문 문자열로 보관한다. 현재 status의 json.loads와 제어 판단은 유지하고 pretty JSON은 JSONL 한 줄로 정규화한다. 같은 owner 프로세스의 기존 GCTiming을 lease 전부터 종료까지 관측하고 콜백을 제거한 뒤 owner_gc_timing.json을 쓴다. 종료 후 파일 I/O만 수행한다. 원본 capture/heartbeat 시각,300ms lease,50ms timer,ROS 소유 스레드와 GC 정책은 그대로다. 원문 기록의 메모리 부담 감소는 검증했지만 실제 MISSION_EXPIRED 해결은 미확인이다.

실제 handoff 함수로 정상/예외·원문/pretty JSON·legacy 경계를 시험한다. 최초2 FAIL/1 PASS(3.49초)는 새 원문/계측 계약 부재였고 구현 후 관련4 PASS/3.41초였다. 예외 경로까지 추가한 전체 회귀 결과는 PROGRESS에 기록한다. 이는 DDS·물리 성공 시험을 대신하지 않는다.

v21 정확한360개 실행 소스 archive SHA256 fe51caeb746f9f10cfcaff63a80e581a759b97f3968d1f40cc206d66d924bd87, 모델 제외 raw49,801,676bytes/SHA25695ae5a46f7d0a476bb4837b310bd3ec37b4b3ace40fa320cbdc71736c1b49c5f. 사후 hash 보존이며 새 실행 증거가 아니다.

### v22 실제 확인: 이번에는 만료 없음, 원인 확정은 유보

UUID ab482f62-ea28-462d-a176-235c58573edb는 BT SUCCESS/정상 종료와12 child·worker 회수까지 완료했다. 실제 heartbeat9,012회에서250/300ms 초과 공백0회, 최대235.980ms는 종료 부근이고 GC와 겹치지 않았다. owner gen2 GC2회65.110/63.029ms는94.849/111.147ms 발행 간격과 겹쳤다. GC 정책은 그대로다. 원문 journal 외에도 owner에 다른 장수 객체가 있으므로 사후 작은 실험의17ms가 실제 프로세스 전체 상한은 아니다. 이전364ms 사건의 원인 해결이나 반복 성공을 입증하지 않는다. owner_deadline_analysis_v22.json과 owner_gc_timing.json으로 수집/발행 시각을 보존했다.

최종 trial은 물리 carry_height 기준 때문에 FAIL이다. 물체 world Z 하강20.094314mm, 같은때 TCP world Z 하강18.406087mm, 상대 이동3.977737mm였고 전체 운반의 TCP 기준 최대 상대 이동5.299600mm·환경 지지힘0N이었다. 기존 pick_monitor는 회전까지 포함한 rotation.T@(target-tcp)를 기록하며 기존 pick_acceptance도 이 상대 좌표로 slip을 평가한다. 높이와 상대 유지의 구분은 carry_frame_analysis_v22.json의 별도 진단이며 원래20mm 기준과 trial을 고쳐 PASS로 만들지 않는다.
