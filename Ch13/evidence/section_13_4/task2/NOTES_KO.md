# 13.4 센서 연결 중간 검증

이 기록은 센서 smoke 결과이며 13.4 전체 완료 판정이 아니다. YOLO, 3D 오차,
시선 추적, 기존 런타임의 엔진 회귀는 아직 검증하지 않았다.

- 기준 제품 커밋: 50324ed 이후 Task 2 변경 상태. 최종 검증 코드 SHA는 최종 보고서에서 별도 기록한다.
- ROS 2 Jazzy + Gazebo Harmonic, 외부 MuJoCo 플러그인 c261f5552edf124d1000a23fb25b6c07cadeb807.
- 실행: `source /opt/ros/jazzy/setup.bash`, 고정 MuJoCo 의존 workspace 및 Ch13/install13_4 설정 후
  `python Ch13/scripts/probe_sensors_13_4.py --engine <engine> --output-dir <새 경로> --timeout 90`.
- 실제 시험은 ROS domain 143(MuJoCo)/144(Gazebo)에서 순차 실행했다.

## 결과 위치

- sensors/mujoco: 첫 실패. RGB-D는 수신했으나 컨트롤러 파라미터 전달 오류로 관절 TF가 없었다.
- sensors/mujoco-replay: 단일 짧은 YAML로 수정한 센서 smoke. 모든 컨트롤러 활성 완료까지는 기다리지 않았다.
- sensors/gazebo 및 gazebo-replay: 센서 검사는 통과했으나 부모 종료 후 자식 잔존을 후속 audit에서 발견했다.
  이 두 PASS 파일은 정상 종료의 근거가 아니다. 확인된 자체 PGID138183의 잔존 자식만 종료했다.
- sensors/gazebo-final: 네 컨트롤러 active, RGB43/depth41/Info43/odom140,
  촬영 시각 TF·320×240 optical frame 확인. 종료 서비스 응답 true,
  강제 종료 없음, 살아 있는 자체 프로세스 잔존 0.
- sensors/mujoco-final: 네 컨트롤러 active 및 clipping 수정 후 센서 검사.
  네이티브 CameraInfo의 R=0을 후속 분석에서 확인했으므로 엄격한 정류 입력 검증의 근거로 쓰지 않는다.
- sensors/mujoco-calibrated: 좁은 범위의 CameraInfo 어댑터 적용 후
  RGB67/depth93/Info93/odom541, R=identity, 촬영 시각 TF, 네 컨트롤러 active,
  강제 종료 없음, 살아 있는 자체 프로세스 잔존 0.

## 교정 및 제한

URDF 고정축 RPY와 MJCF intrinsic Euler 순서 차이는 명시적 quaternion으로 교정했다.
카메라의 기존 -1.5708 pitch는 -π/2로 정규화했으며 기존 물리 장착 위치·질량은 유지했다.
추가 가상 프레임은 질량·충돌이 없고 vision_enabled=true일 때만 URDF에 추가된다.

MuJoCo의 visual clipping은 statistic.extent로 스케일되므로 시각 전용 extent=1,
near=.1/far=5로 고정했다. 고정 CameraPlugin은 K/P/D는 채우지만 R은 0으로 둔다.
Ch13 어댑터는 알려진 무왜곡 pinhole 계약만 검사하고 R을 identity로 설정한다.
원본은 /native/camera_info에 유지하며 다른 왜곡·ROI·binning·frame은 거부한다.
외부 플러그인 소스는 수정하지 않았다.

자체 launch 부모가 끝났다는 사실만으로 종료 성공을 판정하지 않는다. 실제 descendant 회귀와
자체 프로세스 그룹의 살아 있는 PID 목록을 사용한다. Gazebo의 gz_frame_id 확장 태그 경고와
MuJoCo pal_statistics의 종료 시 context-invalid 메시지는 로그에 남겼다.
MuJoCo 종료 프로세스는 0으로 끝났지만 이 메시지가 없었다고 보고하지 않는다.

RED/GREEN 로그와 실제 RGB PNG·depth NPY·CameraInfo·TF·시각 표본은 인접 파일에 보존한다.
