# 13.4 시간 정합·융합 중간 검증

기준: Task 2 커밋 d45d84e 이후 변경. 이 단계는 실제 엔진의 3D 오차/YOLO/팔 추적
완료 판정이 아니며, 합성 ROS 입력을 사용한 통신·기하 계약 시험과 구분한다.

`full.txt`: Ch13 기존·신규 테스트와 vision 패키지 테스트를 함께 실행해 99개 통과.
`build.txt`: ROS Jazzy와 고정 MuJoCo 의존성만 불러온 환경에서 Ch13 네 패키지 빌드 통과.

검증한 경계:

- bounded RGB/depth 각 10개, CameraInfo 5개, 최신 작업 대기 한 개.
- RGB 원본 촬영 시각 일치, depth skew 30ms, CameraInfo age 1초, 동일 frame/해상도.
- RGB payload/stride/encoding 검사, 정류·정합/왜곡/ROI/binning 검사 및 calibration 변경 폐기.
- 300ms ROS age·monotonic age·clock 정지, 역행 epoch 및 처리 후 재검사.
- 실제 tf2 Buffer에 t=1.0의 이동 0과 t=1.15의 이동 1m를 넣고 t=1.0 관측이
  최신 TF가 아닌 촬영 시각 TF로 변환되는지 확인. zero/disconnected/범위 밖 TF 거부.
- 실제 ROS publisher/subscriber로 원본 촬영 시각을 보존한 PointStamped 발행 확인.
- depth 범위 파라미터는 기본 0.1–5m이며 유한·양수·순서 검사를 수행한다.

최초 전체 실행에서 98개 assertion은 통과했지만 종료 시 미회수 Destroyable 예외가 출력됐다.
별도 ROS 프로세스 회귀 시험으로 재현하고 실패를 확인했다(`shutdown-red.txt`).
원인은 설치된 rclpy MultiThreadedExecutor의 shutdown에서 guard를 파괴한 뒤 마지막
pool callback이 guard를 사용하는 경합이었다. ROS 콜백에는 무거운 처리를 두지 않으므로
새 시각 프로세스만 SingleThreadedExecutor로 단순화했다. 깊이 처리와 TF 대기는 별도
작업자에서 수행해 ROS TF 수신이 진행된다. 기존 13.3 제어 실행기는 변경하지 않았다.
최종 99개 실행에서는 미회수 예외가 없었으며, 자식 프로세스 출력 검사도 포함했다.

위 검사는 고정된 허용 오차/단위/소유권 계약의 시험이다. 보행 정책, YOLO 의미 인식,
실제 엔진 영상의 위치 오차·시선 추적·파지 능력은 이 기록으로 주장하지 않는다.
