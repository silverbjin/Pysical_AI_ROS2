# G00 자산·원고 계약 감사 (2026-11-26)

판정: PARTIAL / BLOCKED. 사용자 승인으로 검수 원본 silverbjin/Pysical_AI_ROS2를 확정. main 9431fb535ce7a51416c19c4395fb2ba3fabdad40 재조회 일치; feat/ch14-ai-deployment 신규 생성. Ch01~13, main, 기존 PR 변경 금지. S2 개정 원고 직접 대조 완료(26쪽, 19개 코드 번호); SHA256 0ca3425f57c3608a5078edb5a8c708dc1d734459072532f9954634695df2b3a6. S1/S3 전량 직접 대조 미완료. 명세 SHA256 ad1c6fc00f862d31687c00e2f99f6ba509a19a4ce142d510ae1b44f71c97f2f1. 저작 원고 자체는 공개 Git에 넣지 않는다.

## 저장소 비교 (이전 실제 Git tree 조회)
| 장 | 검수 원본 tree | 복제본 tree |
|---|---|---|
| Ch07 | 91f087fa956037fc505db1899ed65439995978ff | 0100bed2a298d751e5c045860341dd960918632d |
| Ch11 | 82770f5da31e6ddd9ae8a404d7cdc621c541e127 | f8ff5151b6272b29d0dc41ad7890115b3255b463 |
| Ch12 | 9f2faa33556f86481a08ee81917e7380d7e0f24a | 9f2faa33556f86481a08ee81917e7380d7e0f24a |
| Ch13 | 85dfb9b17fbcfc5e15f460fe0d64153521fe2fb3 | 94bfd11aac6018145bb80e1c21a8addd721dd225 |
복제본 HEAD 47f3a9b49e74d2cc99b0c61d3b5edb4668ae2e90. 전체 병합 불필요.

## 원본 계약
Ch07 vision_basics: /camera/image_raw, /camera/depth/image_raw, /camera/camera_info. 공간 정렬 및 실제 의미 검출은 G03 검수. §7.7 BLOCKED 보존. Ch11 my_quadruped_bot: xacro common/parts, empty_world, ros_gz_bridge; /clock, /joint_states, /imu/data_raw, 12개 Float64 cmd_pos(ROS) → /0/cmd_pos(GZ). Ch12 load_bundle은 manifest/schema/normalization/task/space 검사; 기본 best_model/best_model.zip. tree 506 entries, release 0개, ZIP 미발견; 외부 artifact/owner bundle 미확보. 실제 모델 신뢰·해시 검사 전 역직렬화 금지. 없으면 명세의 2048 transitions smoke 1회만 허용. Ch12 ROS controller는 robust도 허용하나 Ch14는 locomotion 한정. Ch13 geometry/contracts: aligned 16UC1 mm/32FC1 m, stride/endianness, median/MAD(0.03m), depth 0.1~5m, deprojection, rigid transform, 양수 capture stamp. 기존 Go2+Piper 300→12 ONNX 제외(권리와 의미 불일치).

## 역사적 실행 기록 (새 PASS 아님)
Ch12 §12.8 MuJoCo/Gazebo result.json: 401/334 active samples, 50Hz sim, 최저 높이 0.3785295/0.3757967m, 최대 inference 1.483195/13.036444ms, clean shutdown. 2048-transition smoke로 보행 품질 미인수. 원본 verifier는 90s 준비, 8s 측정, >=100 active, 35~55Hz, height>0.14m; joint count 기록만 하며 직접 assert 및 관절 실제 응답 비교 보강 필요. controller min height 0.2m와 별개. 미래 시각 tolerance 50ms, tilt45°, command ±3, 250ms sensor, 100ms skew, 500ms command/watchdog, 20ms infer, 0.1rad step. G08 기존 보호 약화 금지. Issue #118 open.

## 라이선스·차단
Ch07/11 package.xml TODO, Ch12 Python pyproject license 미선언; vendor 전 권리 확인. Ch12 ROS와 Ch13 vision Apache-2.0 선언, Ch13 LICENSE 존재(별도 third-party notice 검사 필요). Ultralytics AGPL/Enterprise 조건 및 가중치/이미지 별도 권리 확인. 바이너리, 원고, 제3자 코드 미복제. 모델/fixture SHA, 실제 PPO checkpoint, Ubuntu24.04/Python3.12/Jazzy ABI, lock 미확정. 작업 컨테이너 Debian13/Python3.13.5/Torch2.10.0+cpu/NumPy2.3.5/OpenCV4.13.0, ROS/Gazebo/Docker CLI 없음, GitHub DNS 실패, onnx/ORT/Ultralytics 없음. 원격 연결 API로 Git만 작업. CPU 기본 환경 candidate resolution 및 검증부터 진행. G00 전체 PASS 금지; 모델 자산 없는 관련 기능만 차단.
