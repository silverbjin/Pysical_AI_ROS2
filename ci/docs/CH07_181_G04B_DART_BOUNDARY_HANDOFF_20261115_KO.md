# Ch07 Issue #181 — DART 6.13 관절 고착 해소 및 미완료 운반/배치 인계 (2026-11-15)

## 검증·보존 원칙

저장소 `silverbjin/Pysical_AI_ROS2`; 기준 `main=9431fb535ce7a51416c19c4395fb2ba3fabdad40`. 원래 G00–G04A의 성공 결과는 재시험하지 않았다. **G04B BLOCKED, G05 NOT_RUN, Ch10 HOLD**. 실제 시험의 원본 SHA와 Artifacts는 절대 혼용하지 않는다. 모든 실험은 Gazebo headless CI 시뮬레이션이며 Owner WSL2/실물/원본 URDF 전체 통합 인수 아니다.

## 이번 개발에서 실제 확인된 3개 물리 경계

| 목적 | 소스 SHA | 실제 CI / 원본 Artifact | 물리적 사실 / 판정 |
|---|---|---|---|
| Finger1 2mm 고착 실측 | `0ed906243d91223a40672cc1af8fcc95538ad6f9` | Run [43710243296](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43710243296), Artifact 14159808199 | JTC reference+hardware cmd **2mm**, native ECS finger1 velocity command **0.01999998m/s** 그러나 real q 이동 **1.46e-9m**; finger2 2mm PASS. ZIP SHA256 `37b95fd2fe2e5098f8153c82752ec6395d84ad1d1236254616773ee4d52fefbb`. |
| 순차 2mm 가설 기각 | `42c056f7d92c3fcd729f626eafb490cc74c85526` | Run [43711161701](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43711161701), Artifact 14159759695 | finger1 단독 2mm도 native 미이동, hardware/ECS 명령 전달. 해당 코드 롤백. ZIP SHA256 `151c0720561e4005085865052990a5522c33e248b398ef81f1d8b7eef0d3ad08`. |
| DART6.13 물리 하한 1mm 테스트용 확장 | `3dcb96c3a1cc308363e533063565a3d3a973327c` | Run [43712237998](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43712237998), Artifact 14161296623 | 실제 두 손가락 0.001899828m, 동적 물체 native 양측 접촉, 상승 **0.11233m**, 1.3s hold drift **0.0003636m**, 고단 운반 custody **0.005361m**, 목적지 XY 오류 **0.013917m**. 하강 `joint3` 실제 오차 0.134865rad로 FAIL. ZIP SHA256 `79d0ae6fcf881f261731797e086f39424a4c4d0e18afe375acfc8fae17b32f93`. |

**원인 확정 수준**: DART `libdart-core+collisions+odelcpsolver6.13 6.13.2+ds1-1~osrf2~noble`의 하한 서보 고착은 테스트 SDF에서 두 original prismatic `axis/limit/lower`만 `0→−.001m`로 바꾼 A/B 시험으로 해소됨. [Gazebo upstream #1684](https://github.com/gazebosim/gz-sim/issues/1684) 사례와 부합하나, **원본 URDF 물리 한계 그대로의 완주 검증은 아님**. 원본 7관절의 ROS Goal/제어·충돌 형상, rod 물리는 바꾸지 않았다.

## 후속 서로 다른 2회 물리시험 (실패 단계 변화)

- Run [43713755831](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43713755831), Artifact **14161133426**, source `a8c4e782dde25c17d3e2689fb62b7ae89bc5e818`, ZIP SHA256 `fc8460aa0221497ea824b736ccd9f6c585653efb53e70efd546864439b0d6946`. 기존 하강 로직에 한정한 strict FJT 후보를 추가했지만, **하강 전에 상단 MoveGroup 자체의 실제 joint2 오차 0.0132844492rad >0.010rad**로 중단, 하강 strict FJT는 미실행. 진짜 rod lift **0.14865m**, hold drift **0.000388m**, 목적지 상공 native rod `[0.530989,0.244177,2.07302]`. 첫 실패는 상단 정밀 피드백.
- Run [43714625440](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43714625440), Artifact **14162335655**, source `a7ced054e024ce4eeac24584d113346cdc34b049`, ZIP SHA256 `433a6b3898eabd7ff4f5debb96888d01456d2ed09e3c4218cad34815744badab`. 상단의 오차 `joint2≈0.01253rad`를 기존 실제 5관절 FJT로 한번만 정착시키도록 시도했으나 **Action ABORTED error -5**, `joint2 desired=0.105683816858`, `actual=0.093309155752`, 잔차 **0.012374661106rad**. 다른 4개 관절은 목표 근접. 실제 rod lift **0.13416m**, hold drift **0.00190585m**, 상단 bin 근처 위치 `[0.532645,0.245626,2.07213]`. 원본 임의 물체 attach 없음. 하강·release·settled ROI 미실행. **해당 상단 FJT 변경은 실패했으므로 작업 브랜치에서 원복**, 원본 두 Artifact와 이 문서로만 보존.

## 다음 원인 경계 (새로운 Gazebo L2 금지)

직접 FJT에서도 q2가 움직이지 않은 이유는 현재 원본만으로 **Gazebo arm joint2 command interface vs native joint2 velocity/position vs 동시 접촉/제약** 중 어디인지 확정할 수 없다. 다음은 기존 원본 ZIP의 `controller_manager`, `gazebo`, 원본 native contacts를 오프라인으로 대조하고, 필요하면 과거 #187과 같은 read-only ECS 계측에 **joint2 하나만** 추가해 첫 실패를 좁혀라. 원본 증거가 재활용 가능하면 새 물리 CI는 실행하지 않는다. 재시험하더라도 반증 가능한 단일 원인 확인이 먼저다.

L0 성공·손가락 2mm 성공·lift 13cm는 **G04B Pick-and-Place 완주 PASS가 아님**. 실제 final ROI, release, settled bin ground-truth, independent native contacts, 모든 안전 판정이 같은 실제 세션에서 충족돼야 G04B 성공을 주장할 수 있다. G05 실제 RGB-D→MoveIt→전체 물리 시연은 아직 NOT_RUN.

새 단계의 장시간 PPO 재학습, Ch10 IK/보행, Ch09 심화 마찰, Ch13 전체 연속 미션은 이번 Issue #181 경계와 별개다.
