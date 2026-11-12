# Ch09 기립 자세 · Ch11 SLAM 지도 저장 — 범위가 고정된 추가 실측

## 재사용과 배제

- **Ch10 Issue #123은 HOLD**이며 체크아웃·빌드·실행하지 않는다.
- 이전 Ch09 12관절 명령·상태 PASS, Ch11 EKF·TF·`/map` 발행 PASS를 유지한다. 그 자체를 이번 새 PASS로 승격하지 않는다.
- 기존 `ci/docker/next_scope.sh`만 선택 모드 `BOOK_STANCE=1` / `BOOK_MAP_SAVE=1`로 확장한다.
- 기존 GHCR 베이스 `ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f` 재사용, 베이스 재빌드 없음.
- Ch11에 베이스에서 누락된 `robot_localization`, `slam_toolbox`은 기존 CI대로 실행 컨테이너에서 설치하고 `addon_versions.txt`에 보존한다. 불변 베이스 이미지와 일시적 최종 런타임은 다르다.

## Ch09 기립 물리 자세 검수

원본 `stand_up`을 실행하고 **실제 Gazebo OdometryPublisher로 계측한 몸체 위치·자세**를 ROS로 브리지한다. OdometryPublisher는 CI에 한하여 xacro로 변환한 URDF에 추가하는 측정용 플러그인이다. 교재 Xacro·12개 컨트롤러·관절·충돌·마찰·world는 수정하지 않는다.

PASS 조건: 시뮬레이션 odom 샘플 50개+, 8개 다리 관절을 가진 /joint_states 샘플 30개+, nonzero timestamp 40개+, 마지막 4초의 몸체 z 최소 0.12m, roll/pitch 절대 최대 20도, z 이동폭 0.08m 이하, xy 수평 이동 0.20m 이하. **발 접촉력과 지지다각형·3회 독립 재현·장시간 강건성은 미검증**. 이 경우의 PASS는 '원본 명령 이후 자세 안정성 대리 지표'에 한정한다. FAIL 시 실제 높이·기울기·드리프트 원시 수치와 bridge/Gazebo 로그를 보존한다.

## Ch11 지도 저장 검수

원본 `slam.launch.py`, `slam_toolbox`, `ekf.yaml`, scan filter를 사용하여 Lifecycle active와 /map 발행을 먼저 확인한다. 이후 실제 `/slam_toolbox/save_map` 서비스 (`slam_toolbox/srv/SaveMap`)를 호출한다. `book_ch11_map.yaml`과 이미지 PGM 파일을 찾고 헤더의 width·height, `resolution`, `origin`, PGM 정확한 픽셀 수, 비미확인 셀 40개 초과, YAML 및 PGM SHA-256을 확인한다.

**지도 정확도·SLAM 루프 폐합·맵 재로딩/내비게이션·로봇 실기/GUI·지속성은 검증하지 않는다.** 서비스가 응답했더라도 파일 또는 비미확인 셀이 없으면 FAIL.

## 산출물

- 공개 Actions: `Book Ch09 posture and Ch11 map save (Ch10 HOLD)`
- 각 독립 Job이 종료코드·첫 실패 단계·원본 `stance_verdict.json` 및 `map_save_verdict.json`과 생성된 YAML/PGM을 Artifact로 보존한다.
- 실패하면 이미 PASS한 Ch05·Ch08·Ch09·Ch11 기존 증거를 다시 검증하지 않고, 오류를 유발한 새 경계만 수정한다.
- 비정상 종료는 PASS 금지. 원인 구분 후 PR 병합 여부 결정한다.


## 실제 실패와 지도 저장 방식 변경 기록 (2026-11-12)

- 첫 공개 CI [#43232612091](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43232612091): Ch09는 **기립 자세 FAIL** (최대 roll/pitch 40.7088° > 20°). [Issue #129](https://github.com/silverbjin/Pysical_AI_ROS2/issues/129)에 실측 원본 기록. 반복 검증하지 않음.
- Ch11 첫 호출은 `slam_toolbox/save_map` 서비스에서 `result=255`, `nav2_map_server` 패키지 누락. 두 번째 호출은 nav2_map_server 일시 설치 후에도 `result=255`, `Failed to spin map subscription`. ROS Jazzy Nav2 MapSaver의 기본 수신 대기 시간은 2초이므로 짧은 timeout이 주요 경계다.
- 이 후속 검수에서는 기존 `slam_toolbox/save_map` 서비스가 통과했다고 주장하지 않는다. **공식 `ros2 run nav2_map_server map_saver_cli`에 `save_map_timeout:=15.0`, `map_subscribe_transient_local:=true`를 지정**하여 동일한 실제 /map을 저장하는 별도 경로로 검수한다. YAML·PGM·실제 비미확인 지도 픽셀 40개 초과와 SHA256이 확인되기 전까지 지도 저장 PASS 불가.
- 원본 `slam_toolbox/save_map` 서비스 실패와 Nav2 MapSaver CLI 결과는 독립 판정이며 혼동하지 않는다. Ch11의 기존 EKF / TF / SLAM Lifecycle /map 토픽 발행 PASS는 별도로 보존한다.
