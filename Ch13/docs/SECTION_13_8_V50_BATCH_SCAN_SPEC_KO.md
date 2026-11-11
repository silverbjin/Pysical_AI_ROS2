# v50 실제 ray 계산 경계 보완 명세

정상 완주 기준 유지·Owner 인수 보류. v49는 관측 만료가 아닌 engine safe-command receipt301.335ms 초과로 정지했다. 정지 직전 Scan124.571ms와 연속 capture_sensor100~173ms 구간을 보존했다. 당시 관측은 유효했다. 다른 층위의 실패를 관측 수명 문제로 합치지 않는다.

## 조사와 채택/기각

공식 Jazzy rclpy spin_once는 Node를 추가·제거하는 경로가 있지만, 독립 domain138의 동일 1kHz timer/각2초 비교에서 per-spin CPU .539/.497초, persistent .480/.615초로 일관된 이득이 없었다. 따라서 executor 재구성은 채택하지 않는다. 이 작은 측정은 실제 프로세스 CPU/정지 원인 재현이 아니다.
https://github.com/ros2/rclpy/blob/jazzy/rclpy/rclpy/__init__.py

설치 MuJoCo3.13.0의 공식 mj_multiRay API와 MultiRayEqualsSingleRay 테스트를 확인했다. 같은 원점의 실제 ray를 한 C 호출로 묶으며 world map 조회나 모의 Scan이 아니다.
- https://github.com/google-deepmind/mujoco/blob/3.13.0/test/engine/engine_ray_test.cc
- https://github.com/google-deepmind/mujoco/blob/3.13.0/src/engine/engine_ray.c

공식 이슈3731은 회전된 inertial frame과 중심 오프셋이 있는 몸체에서 누락 가능성을 보고한다. 이슈3736은 일부 tall geometry에서 일괄 방식도 느려질 수 있음을 보고한다. 구현 전에 읽었으며 API 존재만으로 채택하지 않는다.
- https://github.com/google-deepmind/mujoco/issues/3731
- https://github.com/google-deepmind/mujoco/issues/3736

v49 저장 자세30개/5,430 rays 비교에서 거리·hit/no-hit 전부 일치(최대오차0m)했다. group5 몸체는 world0과 알려진 원통 target26이다. 독립 JSON thread와의 경합 비교에서 scalar wall36.985~64.321ms, batch5.505~10.880ms였다. scheduler/GC/GIL 정책과 physics/ROS/action/lease는 바꾸지 않았다. 이 실험은 전체 엔진 부하나 안전 성공 보증이 아니다.

## 한정한 순차 작업

1. RED: 실제 MuJoCo 작은 모델에서 Level2의 지원 범위는 ray 하나씩 호출하는 대신 한 batch 호출로 같은181거리/필터/원점을 산출하도록 기대하고 실패를 확인한다. 회전 중심/offset 몸체와 다른 profile의 기존 scalar 경로도 검사한다.
2. GREEN: 정확한 설치3.13.0/carry_v1/Level2에만 적용한다. world 몸체 또는 몸체 inertial 원점에 중심이 일치하는 대칭 primitive만 batch 적격으로 제한한다. non-world body의 전체 geoms가 centred sphere/capsule/ellipsoid/cylinder/box인지 확인하며 offset/mesh/알 수 없는 경우 기존 mj_ray로 돌아간다. 알려진 이슈에 맞춰 라이브러리나 물리 모델을 고치지 않는다.
3. 원점은 기존 post-step kinematics와 SCAN_POS, 방향181개와 group5/static/bodyexclude·.05~4m 필터를 그대로 유지한다. cutoff는 공식 테스트처럼 mjMAXVAL로 두고 기존 거리 필터를 적용한다. qpos/물리/명령/주기/수명/TF/소유권은 바꾸지 않는다. sensor summary는 실제 선택 backend를 기록한다.
4. REFACTOR/자체 REVIEW/전체 회귀/COMMIT/공개 CI 실제 runner·steps 확인 후 별도 freeze/build/audit/runtime 일치를 확인한다.
5. 같은15Hz/overlap1/전진DUBIN+RPP/계측1의 새 UUID 단일 실제 사례에서 Scan 지연·최초 실패·액션·종료를 검증한다. 정상 연속 성공 전10회 평가/Owner 인수로 넘어가지 않는다. 임계값300ms/TF100ms·원래 최종 수치는 유지한다.

새 executor/worker·시뮬레이터·인식·제어기·WBC·정책 학습은 범위에 없다. API batch 재사용에 한정한다.
