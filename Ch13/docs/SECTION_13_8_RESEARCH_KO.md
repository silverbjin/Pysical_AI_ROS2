# 13.8 공식 패턴 조사와 채택 근거

2026-11-04 KST. 외부 예제의 존재를 이 로봇의 물리 성공으로 표현하지 않는다. 실제 결과는 별도 보고서와 UUID별 증거에 있다.

| 확인한 공식 소스/ref/파일 | 확인한 패턴 | 채택과 차이 |
|---|---|---|
| [MoveIt2.12.4 planning_scene_interface.cpp](https://github.com/moveit/moveit2/blob/2.12.4/moveit_ros/planning_interface/planning_scene_interface/src/planning_scene_interface.cpp) | ApplyPlanningScene 응답 확인, world/attached collision 객체 분리 | 기존 Planner의 실제 서비스 wrapper와 symmetric ACM diff를 재사용. LOWER에서 대상–지정 받침대만 계획 접촉을 허용하고 해제 후 복원. 다른 로봇/환경 충돌 규칙은 유지. C++ nested spin을 Python owner에 복사하지 않음. planning attach는 물리 weld가 아님. |
| [ROS Jazzy rclpy action/client.py](https://github.com/ros2/rclpy/blob/jazzy/rclpy/rclpy/action/client.py) | send_goal_async의 goal_uuid 인자; cancel_goal_async/get_result_async의 별도 future | 귀환 UUID를 engine에 사전 예약·확인한 뒤 실제 goal을 보냄. 취소 ACK와 terminal/물리 정착/회수를 분리. 기존 GoalTracker/DeferredClients 재사용. |
| [rosbag2 0.26.11 simple_bag_recorder.py](https://github.com/ros2/rosbag2/blob/0.26.11/rosbag2_examples/rosbag2_examples_py/rosbag2_examples_py/simple_bag_recorder.py) | CDR 직렬화·TopicMetadata·SequentialWriter 및 node clock 기록 | 설치 rosbag2/rosbag2_py0.26.11 확인. 학생 실행에서는 공식 ros2 bag CLI로 선별 토픽/--use-sim-time 기록, 정상 닫기와 metadata를 별도 확인. 원본 capture timestamp/receipt를 bag receipt로 치환하지 않음. |
| [ROS Jazzy QoS override 원본](https://github.com/ros2/ros2_documentation/blob/665b15d970cd1ee8a2d0301c673159a3c5092228/source/How-To-Guides/Overriding-QoS-Policies-For-Recording-And-Playback.rst) | topic별 compatibility와 --qos-profile-overrides-path | 전 토픽 Best Effort 전환 대신 실제 publisher QoS를 따른다. static TF durability를 보존. docs.ros.org 본문 차단으로 공식 GitHub 원본을 읽음. |
| [ROS Jazzy ros2topic delay.py](https://github.com/ros2/ros2cli/blob/jazzy/ros2topic/ros2topic/verb/delay.py) | 수신 시 node clock과 header stamp의 차이 | 원고의 존재하지 않는 토픽명을 복사하지 않고 실제 observed_target/observation을 설명. health.json에서 sim delay와 촬영 monotonic 나이를 따로 측정. 서로 다른 clock domain을 빼지 않음. |
| [MuJoCo3.13.0 specs_test.py](https://github.com/google-deepmind/mujoco/blob/3.13.0/python/mujoco/specs_test.py) | MjSpec의 add_body/add_geom, pos/quat/size, type | 설치3.13.0과 같은 ref의 공식 시험을 읽음. Level2의5도 기하 확장 근거. 아직 경사 보행·Level3 물리 성공 증거는 아님. |

py_trees_ros2.6.0의 nonblocking tick/INVALID 취소, Jazzy callback ownership 패턴은 기존 SECTION_13_7_RESEARCH_KO.md의 실제 설치 대조 결과와 소스를 재사용한다.

## 프로젝트에서 추가로 검증해야 하는 부분

공식 MoveIt/rclpy 예제를 합친 것만으로 Go2가 물체를 운반하는 안전 계약이 생기지 않는다. 운반 phase·고정 팔·예약 goal·연속 tactile contact·fresh camera health·정지 후 fresh3D 재획득은 이 프로젝트의 설계다. v2 실제 실행에서 관측 부분 가림과 정상 force-hold의 차이를 확인한 후 이 경계를 명시적으로 분리했다. 사후 physics verdict는 실제 freejoint/contact 로그를 평가하며 제어 입력이 아니다.

Jazzy MTC 예제의 추정 경로 한 곳은 GitHub 조회에 실패해 채택 근거로 사용하지 않았다. 실행된 기존 Planner와 위2.12.4 공식 서비스 원본·설치 메시지 타입·자체 부품 시험을 근거로 썼다.
# 귀환 quaternion 재확인

[ROS Jazzy 공식 Quaternion-Fundamentals 원본](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Intermediate/Tf2/Quaternion-Fundamentals.rst)을 재조회했다. ROS 순서(x,y,z,w), norm1, Python에서 네 성분을 명시하는 패턴을 적용한다. 설치 메시지는 실제로w=1 기본값이며 기존 continuation은z만 덮어써 오류를 만들었다. 수정은 planar yaw의sin(yaw/2),cos(yaw/2)를 포함한 전체 성분 설정이다. 이는 입력 표현의 수정이며 실제 귀환/내려놓기 성공을 대신하지 않는다.

[MuJoCo3.13.0 XMLreference.rst](https://github.com/google-deepmind/mujoco/blob/3.13.0/doc/XMLreference.rst)의 body/camera를 GitHub connector로 읽었다. fixed 모드는 body-relative pos/quat, MuJoCo view는-Z/up+Y이므로 기존 optical 변환diag(1,-1,-1)을 유지한다. 새 설정은 compile 전 camera.pos/quat이며 SensorSuite가 compiled model에서 실제 TF를 생성한다. 3.3.0 검색 문서를 설치 버전 증거로 대신하지 않았다. [PCL 공식 cylinder segmentation](https://pointclouds.org/documentation/tutorials/cylinder_segmentation.html)은 robust plane/반경 제한 패턴만 조사했고 추가 PCL 설치나 runtime 검출기 채택은 하지 않았다. 저장 부분 영상에서 충분한 평면 근거를 얻지 못했기 때문이다.

## 장애물 월드 확장 전 조사: 운반 외형

[공식 Nav2 Jazzy costmap 문서](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/costmap_2d/)와 [Jazzy footprint 가이드](https://ros-navigation.github.io/mkdocs.nav2.org/jazzy/configuration_and_development/first_time_robot_setup_guide/footprint/setup_footprint/)에서 조작 팔/적재물로 외형이 달라질 때 costmap의~/footprint 토픽으로 polygon을 갱신하는 패턴을 확인했다. 기존 footprint.json은13.5의 제한된 관측70샘플과4cm margin에서 생성됐으므로, 팔을 뻗은 운반 상태까지 포괄한다고 가정하지 않는다. 장애물/문 월드 전 실제 joint/TF와 알려진 부착 형상의 외형을 검사하고 설치 Nav2 source/API와 실제 수신을 확인할 후속 항목이다. 현재 빈 개발 fixture의 v8 실행에는 아직 동적 footprint를 추가하지 않았다. 공식 기능의 존재는 이 로봇의 좁은 문 통과 증거가 아니다.

## 증거 보존 도구

[Python3.12 gzip 공식 문서](https://docs.python.org/3.12/library/gzip.html)의 GzipFile(fileobj,mode,mtime)와 [tarfile 공식 문서](https://docs.python.org/3.12/library/tarfile.html)의 exclusive 생성·fileobj 스트림·regular member 처리를 확인했다. 설치 Python은3.12.3이며 문서는3.12 계열의 동일 API를 설명한다. 기존13.7 archive_evidence.py의 mtime0·원본 보존·모델 제외·SHA256 manifest 패턴과13.6 restore_evidence.py의 경로/타입/hash/기존 파일 불일치 거부를 재사용한다.13.8의 부모 경로만 명시적으로 제한하고 현재 frozen FAIL을 덮어쓰지 않는 도구가 후속 작업이다. 빈 폴더 복원 시험은 기존 실제13.6/13.7 계약과의 호환을 확인하며 물리 재실행으로 해석하지 않는다.

## RGB-D 경계 픽셀 처리

실제 venv SciPy1.18.1을 확인하고 [공식 v1.18.1 scipy/ndimage/_morphology.py의 binary_erosion](https://github.com/scipy/scipy/blob/v1.18.1/scipy/ndimage/_morphology.py)을 읽었다. bool 입력·명시적 structuring element·iterations=1로 경계를 식별한다. 경계 전체를 지우는 실험은 원거리 표면 폭 부족으로 회귀2개가 실패해 채택하지 않았다. 최종 후보는 경계의3x3 red/valid-depth 이웃 중간값보다5mm 이상 앞서는 픽셀만 제외하고 정상 silhouette는 보존한다.

[공식 PCL StatisticalOutlierRemoval 설명](https://pointclouds.org/documentation/tutorials/statistical_outlier.html)의 모델 추정 전 이웃 기반 sparse outlier 선별 패턴을 추가로 참고했다. PCL의k-NN/평균·표준편차 알고리즘을 그대로 포팅한 것은 아니다. 정렬된 RGB-D의 경계에서만 같은 frame 이웃 depth를 비교하는 프로젝트 전용 전처리이며 새 PCL 의존성을 추가하지 않는다. 원통 높이75%·RMS1.5mm·q90 2mm 기준은 유지한다. raw RGB-D/hash/촬영 시각/TF를 보존하며 기본13.6/13.7은 filter_boundary=False다. 실제 v9 거부 frame에서 경계1pixel 제외 후 기존 component 최소 크기와 strict fit을 적용해349 surface points·RMS0.0497mm·높이78.996mm를 확인했다. 전체 회귀와 실제 동작 검증은 별도다.

## 실제 release 후 MoveIt 모델 분리

[MoveIt2.12.4 planning_scene.cpp의 processAttachedCollisionObjectMsg REMOVE 분기](https://github.com/moveit/moveit2/blob/2.12.4/moveit_core/planning_scene/src/planning_scene.cpp)는 특정 ID와 비어 있지 않은 link_name이 실제 parent와 다르면 거부한다. 공식 구현이 허용하는 ID-only REMOVE를 채택한다. 기존 continuation은reuse/tcp ADD 뒤reuse/link6 REMOVE를 보내고 outer ApplyPlanningScene.success만 확인했다. 실제614e 로그와 별도 설치 API probe에서 이 잘못된 요청의 outer true/attached 잔류를 재현했다.

보완은 명시적 소유ID만 제거한 뒤 GetPlanningScene의 WORLD_OBJECT_GEOMETRY/NAMES·ROBOT_STATE_ATTACHED_OBJECTS를 조회해 attached 부재·world 단일 형상·새 관측 중심 일치를 확인한다. 물리 개방과 양 finger 접촉 소실을 먼저 확인하고 release 이후 촬영된 새 원본 RGB-D만 사용한다. 기록된 관측으로 domain136 scene service만 시험했으며 shutdown ACK/exit0까지 확인했다. 실제 액추에이터나 engine은 실행하지 않았다. 공식 장면 API 및 이 probe는 물리 release/retreat 성공 증거가 아니다.

## 반복 관측 지연: 2026-11-05 공식 근거와 적용 판단

[ROS2 Jazzy executor 공식 원본](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Executors.rst)과 [callback groups 공식 원본](https://github.com/ros2/ros2_documentation/blob/jazzy/source/How-To-Guides/Using-callback-groups.rst)을 조회했다. 웹 문서는 접근 차단되어 같은 공식 저장소의 Jazzy 원본을 읽었다. 기본 mutually-exclusive 그룹에 모두 두면 executor의 스레드 수만 늘려도 병렬 처리가 되지 않는다. 긴 콜백·스케줄 순서의 지연을 우선 분해하고 원래 단일 ROS owner를 유지한다.

[ros2/rclpy #1223](https://github.com/ros2/rclpy/issues/1223)은 Iron/Ubuntu22.04/FastDDS에서 MultiThreadedExecutor의 timer rate 하락·CPU 증가를 보고한 재현 코드다. 이 프로젝트의 Jazzy 원인을 증명하거나 해당 제보의 수정이 검증됐다는 뜻이 아니다. 일괄 executor 변경을 회피하고 설치 환경에서 직접 계측해야 한다는 비교 사례로 사용한다.

[Mesa 공식 LLVMpipe 설명](https://docs.mesa3d.org/drivers/llvmpipe.html)과 [환경 변수 문서](https://docs.mesa3d.org/envvars.html#lp-num-threads)를 확인했다. LLVMpipe는 CPU software rasterizer이고 LP_NUM_THREADS는 렌더 worker 수다. 실제GL query는Mesa25.2.8/LLVM20.1.2·llvmpipe를 반환했다. 기존2를 임의로 늘리거나 driver/GPU 설치를 추가하지 않는다. 현재 문서의 기능 설명과 실제 설치 query를 구분한다. render 시작/끝·process CPU를 기록해 queue 지연과 계산/스케줄 지연을 구분한 후 필요한 작은 변경만 적용한다. 원본 capture/TF와300ms 기준은 유지한다.

실제 설치rclpy7.1.12를 package.xml에서 확인한 뒤 공식 [action/client.py 7.1.12](https://github.com/ros2/rclpy/blob/7.1.12/rclpy/rclpy/action/client.py)와 [type_support.py 7.1.12](https://github.com/ros2/rclpy/blob/7.1.12/rclpy/rclpy/type_support.py)를 GitHub connector로 읽었다. ActionClient 생성자는아직 없는 타입 지원을 동기로 import한다. [공식 ROS2 lifecycle 설계](https://design.ros2.org/articles/node_lifecycle.html)의 configure에서 일회 자원을 준비하고 active의 긴 초기화를 피하는 패턴을 참고해13.8의ready에서타입과warmup 모듈을 사전 준비한다. LifecycleNode로 전체를 재작성한 것은 아니다. 기존 client/goal 수명과 단일 ROS owner는 유지한다. 독립 probe에서 arm client98.471→5.420ms였고 준비340.085ms는동작 전으로 이동했다. 실제 live455ms gap의 세부 기여는 새 실제 구간 timing으로 확인하며 idle결과만으로 해결 완료라고 쓰지 않는다.

[Jazzy 실시간 프로그래밍 공식 원본](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Demos/Real-Time-Programming.rst)의 실행 경로에서 비결정적 초기화·page fault·동적 할당과 무한 blocking을 피하는 원칙도 확인했다. 적용은타입 준비의 시점 분리뿐이다. 문서 예제의mlockall/스케줄 우선순위/커널 설정을 이 Windows/WSL 환경에 추가하지 않았고 hard real-time 보장이라고 표현하지 않는다.

## v14 표면 합의점 모델: 검출 계약의 명시적 변경

[PCL1.15.1 공식 cylinder segmentation](https://github.com/PointCloudLibrary/pcl/blob/pcl-1.15.1/doc/tutorials/content/cylinder_segmentation.rst)과 포함된 C++ 구현의 모델 추정→inlier 선별→계수 보정 패턴을 확인했다. 예제의 자유축/normal 추정이나5cm 기준을 이20mm 반경 대상에 적용하지 않는다. 기존 프로젝트는 알려진 upright축과 반경으로 SciPy의soft_l1 두 좌표 중심을 추정한다. 실제 설치 [SciPy1.18.1 least_squares.py](https://github.com/scipy/scipy/blob/v1.18.1/scipy/optimize/_lsq/least_squares.py)의 robust loss 설명도 확인했다.

채택 패턴은 기존 robust 중심에 대해2mm 이내의side점이95% 이상일 때 합의점을 선별하고 중심을 다시 계산하는 것이다. 재계산 뒤에도95% 비율을 다시 확인하며 RMS1.5mm·q90 2mm·side 폭/최소20점·실제 inlier 표면의75~105% 높이를 모두 요구한다. PCL의RANSAC 구현을 복사하거나 호출한 것은 아니다. 새 패키지 설치 없이 기존 고정축/반경 문제에 모델 합의점 검사를 적용한다.

**변경되는 계약:** residual_m의 모집단은13.8 새mode에서 합의점이다. raw_residual_m/raw_points/outlier_points/surface_inlier_fraction과선별기준을 함께 기록한다. 모든 점의RMS 검사를 유지했다고 표현하지 않는다. 심한 손상이나 부족한 높이를 정상으로 바꾸지 않으며 기본13.6/13.7은 기존 전체점 fit을 유지한다. 이전 boundary 이웃 필터는13.8 live에서 끄고 새mode와 누적하지 않는다. 촬영 시각/TF/GID/hash·물리 모델·실행 속도·수명/접촉 경계는 유지한다. v9/v13 실제 거부 영상과 저장 시야 궤적, 25% 깊이 손상/가림 시험을 검증 근거로 사용하며 최종 actual은 별도다.

## v15: Windows reader lock과 advisory 기록의 실행 경계

[Microsoft CreateFileW 공식 문서](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)의FILE_SHARE_DELETE는rename에도적용된다. [WSL #3395](https://github.com/microsoft/WSL/issues/3395)는Windows watcher와rename EACCES의과거비교사례이며동일버전의확정원인으로대신하지않는다. 직접새파일을Windows FileShare.ReadWrite로열고WSL replace를시도해실제PermissionError를재현했다. 이전JSON보존/오류1회기록/owned writer join PASS였다. 기존live실행자료는수정하지않았다.

[Python3.12 queue 공식 문서](https://docs.python.org/3.12/library/queue.html)의bounded producer/consumer 패턴과 [threading.Condition/Thread.join](https://docs.python.org/3.12/library/threading.html)을참고했다. 구현은Condition으로보호한단일pending slot과한개의비daemon writer다. ROS timer는작은snapshot만넘기며파일I/O는writer에서수행한다. 새상태가대기중상태를대체해도한도가늘지않는다. I/O/직렬화오류는advisory delivery기록으로남고기존정상snapshot을유지한다. 끝에서는pending을소진하고join결과를기록한다. join미확인은정상미션성공으로바꾸지않는다. 실제controller/lease/goal/cancel의owner나주기는바꾸지않는다.

## v17: RGB-D에 섞인 MuJoCo site 보조 형상

설치와같은공식3.13.0의 [mjvisualize.h](https://github.com/google-deepmind/mujoco/blob/3.13.0/include/mujoco/mjvisualize.h), [engine_vis_visualize.c](https://github.com/google-deepmind/mujoco/blob/3.13.0/src/engine/engine_vis_visualize.c), [visualization.rst](https://github.com/google-deepmind/mujoco/blob/3.13.0/doc/programming/visualization.rst)를읽었다. geomgroup과sitegroup은별도이며site도시각장면의형상으로추가된다. 기존코드는geomgroup만설정해서붉은attachment_site가센서에보였다. 종료후segmentation41pixel모두동일site임을확인했고sitegroup만off한같은실패자세에서표면합의78.42→100%를확인했다.

채택: latest paired센서stream의MjvOption.sitegroup[:]=0. 외부XML/site좌표·기존geom그룹·물리·추정기95%기준·관측수명은유지한다. segmentation/target truth를live검출에사용하지않는다. legacy옵션은유지한다. 전체336부품PASS는수정된실패장면의회귀를포함하며실제Level1전체성공과구분한다. 자세한원인·반증·버전·한계는SECTION_13_8_FLOOR_VISION_DIAGNOSIS_KO.md에기록했다.
## 바닥 놓기의 action terminal과 접촉 정착

실제설치control_msgs5.10.0 package.xml을확인하고 [같은ref의 FollowJointTrajectory.action](https://github.com/ros-controls/control_msgs/blob/5.10.0/control_msgs/action/FollowJointTrajectory.action)을읽었다. goal_tolerance는관절최종값의허용오차이며물체지지접촉성공을뜻하지않는다. 첫조회4.8.0과구분한다. v17은팔terminal시바닥보다1.7886mm높았고support는5.124567wall초뒤처음발생했다. nativebridge의기존0.05rad/0.05rad/s 관절완료계약을바꾸지않고floor LOWER뒤별도실측저속/지지/정착gate를둔다. 기존pick의저속0.003rad/s/0.5sim초/20wall초정착패턴을재사용하며명시적상한변경과지지없는개방금지를기록했다.

## 원고3cm 목표를 위한 Nav2 설정 검토(아직수정/실제검증아님)

[설치와같은Nav2 1.3.13 SimpleGoalChecker](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_controller/plugins/simple_goal_checker.cpp)를다시읽었다. 현재YAML의xy_goal_tolerance0.06/statefultrue는6cm반경에들어온후XY재검사를중단하고yaw를확인한다. v15귀환50.16mm/v17귀환43.34mm는원고3cm와별도로FAIL이다. 초기navigation오차34.35mm도같은설정으로허용될수있다. 후보는book scenario전용0.015m override이며기본development/기존YAML값은유지한다. body정착드리프트와RPP접근속도·progress checker를실제navigation에서확인해야하며단순파라미터변경을3cm달성으로표현하지않는다. v18의기능검증에는아직적용하지않았다.
## v19: 연결조각과 전체물체 최소점수의 구분

[PCL1.15.1 실제cylinder_segmentation.cpp](https://github.com/PointCloudLibrary/pcl/blob/pcl-1.15.1/doc/tutorials/content/sources/cylinder_segmentation/cylinder_segmentation.cpp)의setInputCloud/segment/inlier추출순서를재확인했다. v18실제거부영상은상부245/하부13pixel이며두조각모두같은엄격한원통모델에맞는다. 기존2D성분별20pixel earlyfilter를전체물체의side20점검사와혼동하지않는다. robust mode에한해작은조각은anchor와의기하결합까지보존하고기존전체모델조건으로평가한다. 기본legacy는유지하고작은조각은단독후보가될수없다. 16개후보/256개전체성분계산상한도유지해많은잡음성분은failclosed거부한다. PCL자유축/normal/RANSAC를실제로사용한것은아니며경계값을이식하지않는다. 자세한원본·음성시험·234자세검증은FLOOR_VISION_DIAGNOSIS보고서에있다.

## v20: 같은 연속 제한 안에서의 시간 배율 세분화

[MoveIt2.12.4 TOTG](https://github.com/moveit/moveit2/blob/2.12.4/moveit_core/trajectory_processing/src/time_optimal_trajectory_generation.cpp)의 속도/가속도 제한에 따른 시간화와 [ros2_control Jazzy 궤적 설명](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/trajectory.html)의 quintic 연속성/overshoot를 확인했다. 실제 제어기는 기존 custom native이며 다른 controller로 교체하지 않는다. v19의1.0배 궤적은 가속도0.109915rad/s²로0.1 한계를 넘었고, 기존1.25배는93.728sim초였다. 같은 연속 proof로1.05909배/79.413sim초를 확인했다. floor opt-in만 feasible coarse 구간의 bounded 탐색과1% 여유를 사용하며 같은 proof를 다시 요구한다. 12회/1%는 프로젝트 선택이며 공식 권장 수치로 표현하지 않는다. 경로와 waypoint·정책/PD·속도/가속도/시간 제한은 유지한다. 자세한 실제 실패·시험·한계는 TIMING_DIAGNOSIS 보고서에 있다.

## v23: Level1 도착 허용 반경의 분리 적용

공식GitHub connector로 Nav2 1.3.13 nav2_controller/plugins/simple_goal_checker.cpp 전체를 재조회했다. xy_goal_tolerance의 제곱 거리 비교와 stateful=true에서 check_xy_=false로 전환하는 실제 구현을 확인했다. v22의44.449mm 정착 오차가6cm 허용 안에 있다는 사실과 원고3cm 목표를 구분한다. Level1 carry_v1 환경에서만 controller_server에 goal_checker.xy_goal_tolerance=0.015를 YAML 뒤의 명시 파라미터로 전달한다. 다른 node와 development/13.6/13.7 YAML, yaw0.06/statefultrue·속도·정책·정착 경계는 유지한다. 1.5cm는 프로젝트의 정착 여유 선택이며 공식 권장값으로 표현하지 않는다. 설정만으로3cm를 달성했다고 쓰지 않고, 실제 GetParameters 읽기와 unloaded navigation1회/정식 navigation판정으로 확인한다. 귀환π회전/적재/장애물의 강건성은 별도다.
