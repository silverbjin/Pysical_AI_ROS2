# Ch07 §7.2 — 실제 Depth/PointCloud2 내용 검증 (Issue #161)

> 기준: ROS 2 Jazzy + Gazebo Harmonic OGRE2, 2026-11-14 KST. **시험 전용 표적 위치를 조정한 조건의 부분 PASS**이며, 원본 장면의 RGB-D 정합/공간 정확도 PASS가 아니다. Ch10 #123 HOLD.

## 이전 성공과 완전히 구분

- [Issue #127](https://github.com/silverbjin/Pysical_AI_ROS2/issues/127)와 [PR #160](https://github.com/silverbjin/Pysical_AI_ROS2/pull/160): 원본 OGRE2 RGB Image/CameraInfo/optical TF 실제 발행 및 종료는 이미 성공. 합격한 RGB-only Gazebo 시험은 **재실행하지 않았다**.
- 본 실습은 아직 미관측이던 **실제 ROS Depth 픽셀과 PointCloud2의 비어 있지 않은 데이터 내용**만 별도로 검증한다.
- 고정 GHCR: `ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f`. Ch07 Xacro blob `629177034e12c38ffe46f635c7e38112e7cc6c2d`, 원래 world blob `54478268aabc5a75a48a0283e1deb7917ce74ddd` 불변.

## RED → 원인 경계 → 최소 조정

1. [첫 CI #43455936806](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43455936806), [Artifact #14053014350](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43455936806/artifacts/14053014350): 새 스크립트의 잘못된 shell 토픽 검사로 조기 실패. 실제 `gz_topics.txt`는 `/camera/depth_image`, `/camera/points` 존재를 증명했다. `grep -Fxq` 정밀 수정만 적용.
2. [다음 CI #43456439428](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43456439428), [Artifact #14054855097](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43456439428/artifacts/14054855097): 실제 ROS `32FC1` depth 8건과 640×480 PointCloud2 데이터를 수신했으나 샘플링한 유한 양수 Depth/XYZ는 **0건**. 유효 내용 판정 FAIL을 유지하고, 단순 토픽 존재를 성공으로 승격하지 않았다.
3. 원본 생성 URDF의 0rad 자세+스폰에서 카메라 높이는 약 **2.29m**인데 원래 월드 `visual_target`의 중심 z는 **1.0m**. 시야각 밖 표적이라는 가설을 분리하기 위해 **CI 실행 중 임시 사본 SDF에서만** 동일 표적 pose z를 2.29m로 조정했다. 원래 world/SDF와 Xacro는 불변이며 변경은 `depth_fixture_diff.json`에 남겼다.
4. 바뀐 조건에 대한 **한 번의 공개 CI #43457034068** SUCCESS; 실제 메시지의 유효 숫자와 종료 상태를 독립 검사했다.

## 최종 실제 증거

- [성공 CI #43457034068](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43457034068)
- [원본 Artifact #14055135443](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43457034068/artifacts/14055135443): 총 28개 파일 직접 검사, ZIP SHA256 `91f5884853db9e2db31a4d70acb79b2453233e01d38efd16b0ac94c3edce5a06`가 GitHub 업로드 로그와 일치.
- 실제 tested PR HEAD `9423c29311af1b1195b2204594a891b6861c2825`, Actions synthetic checkout `e158d6b1ae939e42aec37740dee7362c004eaf61`. 기준 `main=cdc5a644d97242f1374986f4c30c5daa067d879f`.
- `depth_cloud_data.json`: ROS `/camera/depth_image` 실제 **2건**, `32FC1`, 640×480, 1,228,800 bytes, 유효 양수 Depth 표본 **25건/프레임**, 관측 범위 **0.83468–0.83507m**, 서로 다른 타임스탬프.
- `/camera/points` PointCloud2 **5건** 수신, `point_step=24`, `row_step=15360`, **7,372,800 bytes**, x/y/z Float32 offset 0/4/8, 수치상 유한한 XYZ 표본 확인. 대표값 x≈0.83468, y≈0.09561, z≈0.08958 (m).
- `result.json`: `status=PASS`, `last_stage=DEPTH_CLOUD_PASS`, `exit_code=0`, `shutdown=OWNED_GROUPS_EXITED_NO_SIGKILL`; `stages.log`: `GAZEBO_NATURAL_ITERATIONS_EXIT_RC=0`.

**기술적으로 중요한 제한:** `frame_id=camera_optical_frame`은 헤더 문자열 일치만 확인한 것이며, PointCloud2의 XYZ 실제 축이 해당 광학 프레임 관례와 물리적으로 맞는지는 검증하지 않았다. 대표 XYZ에서 x≈0.835m인데 Depth는 ≈0.835m이므로, **좌표축 변환/포인트 대응 관계는 별도 조사 대상**이다. 해당 사실을 덮고 '3D 정합 PASS'로 해석하면 안 된다.

## 판정과 후속 범위

- **SCOPED PASS:** 원본 RGB-D Gazebo 센서 및 ROS-GZ 브리지에서 *테스트용 시야 내 표적*에 대한 유효 `32FC1` Depth 숫자와 PointCloud2 Float32 XYZ 자료 수신, 유효 stamp/frame 헤더와 정상 종료.
- **NOT_RUN:** 원본 z=1m 시험 월드에서 유효 depth 관측, RGB↔Depth 픽셀·시간 정렬, PointCloud2 optical 축/3D 역투영 정확도, RViz/WSLg GUI, Ch07 §7.7 물리 접촉 파지, 실제 하드웨어.
- `Ch07` 전체 PASS 아님. 총괄 #118 OPEN, Ch10 #123 HOLD.
