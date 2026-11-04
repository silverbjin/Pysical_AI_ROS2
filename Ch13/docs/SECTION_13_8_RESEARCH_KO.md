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
