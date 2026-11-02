# 12.6절 장애물 회피 환경 구현·실행 보고서

2026-10-17, 패키지 0.6.0, 소스 기준 커밋 `5a5c88a`와 이후 미커밋 12.6 변경을 검증했다. 최종 통합 커밋은 상위 작업에서 기록한다.

## 구현

`QuadrupedAvoidanceEnv`에 목표 특징 48개와 16/32개 LiDAR를 연결했다. 실제 `mj_ray`와 geom 그룹 필터로 로봇·목표·바닥을 제외한다. 거리 단위 노이즈와 dropout은 스텝별로 캐시하며, 보상에는 깨끗한 거리를 사용한다. 크기가 다른 충돌 박스 10개를 에피소드별로 배치하고 시작·목표·박스 사이 간격을 검사한다.

모든 로봇 geom과 장애물 접촉을 양쪽 피연산자 순서로 검사한다. 물리 하위 스텝의 순간 접촉을 유지하여 종료·-100 총 보상을 적용하고 도착 보상을 차단한다. `fallen`은 별도로 유지해 기립 중 충돌을 낙상으로 세지 않는다. PPO 과제·관측 schema·저장·재생, CLI, RGB/native 광선과 경로, 충돌 진단을 연결했다.

## 실제 검증 결과

| 항목 | 결과와 증거 |
|---|---|
| 12.1~12.6 회귀 | EGL 및 실제 RGB 테스트 포함 109개 통과. `evidence/section12_6/green.log` |
| 순간 접촉 | frame_skip=100, 전방 속도 2m/s에서 시작·최종 접촉은 없지만 중간 접촉으로 종료·-100, 낙상 false 확인 |
| 거리·관측 | 1.8m 실제 광선 거리, yaw 회전, 자기 감지 제외, 16/32차원, 노이즈 시드·캐시, dropout과 깨끗한 안전 비용 확인 |
| 실제 MuJoCo 롤아웃 | 24조합 × 500 = 12,000 제어 스텝. 16/32 rays × 0/0.05m 노이즈 × stand/random × 시드 0/42/123. 관측·보상 유한값, 합계, 목표 여유와 30Nm 토크 한계 확인 |
| 짧은 PPO | 기존 dummy 2,048+128 및 추가 실제 subproc 128 = 총 2,304 학습 전이. 각 실행의 저장·200스텝 재생 확인 |
| 독립 wheel | 0.6.0 wheel을 `/tmp/ch12-126-wheel-only`에 설치하고 `/tmp`에서 import. 저장 PPO로 실제 human viewer 100스텝, geometry 최대 117개, 정상 close와 CLI SIGINT 130 확인 |
| viewer 반복 종료 | 12.1/12.2/12.3/12.5/12.6의 별도 프로세스 15개. 정상 종료 5회·실제 SIGINT 10회, traceback 없음 |
| Gazebo/ROS | 기존 Ch11 패키지 빌드 및 104개 테스트 통과. 실제 센서·TF·기립과 서버 종료 확인 |

12,000스텝 결과는 기존 실제 실행의 `result.json`, RGB는 `frame.png`에 보존했다. stand의 충돌·낙상·도착은 모두 0이었다. random은 전체 12회 중 4회에서 각 1회 충돌했고 도착은 0이었다. 이 실행의 낙상 집계는 충돌 종료를 제외하는 이전 정의로 0이며, 충돌과 동시에 발생한 낙상까지 구분했다는 증거는 아니다. 검증 스크립트도 현재 `info['fallen']`을 직접 세도록 수정했다. 이 정의 변경으로 과거 JSON을 다시 쓴 것으로 취급하지 않는다.

기존 두 PPO 실행의 최종 평가 평균 보상은 1.99352±0.620096 및 1.591059±1.297392였다. 최종 리뷰에서 검증 스크립트가 backend 인자를 전달하지 않아 `subproc` 폴더도 실제로 dummy를 사용했음을 manifest로 발견했다. `backend=backend`를 전달하도록 수정했다. 과거 결과를 덮어쓰지 않고 `ppo_runs/subproc_verified`에서 실제 spawn 방식 2개 환경·16 rays·128전이를 추가 실행했다. manifest의 backend는 subproc이며 파라미터 변화는 0.270348, 최종 평가 보상은 1.526451±1.001309였다. 별도 재생 200스텝의 총 보상은 2.076079, 충돌·도착은 0이었다. 세 실행의 평가 도착률은 모두 0%다. 새 학습·재생 로그는 `subproc_verified_train.log`와 `subproc_verified_play.log`에 있다. 기존 두 실행과 새 실행의 TensorBoard 학습·평가 태그도 확인했다. 기립/random과 짧은 PPO로 학습된 이동·회피 능력을 주장하지 않는다.

Gazebo는 시뮬레이션 8.024~38.046초에서 몸체 높이 0.249166~0.250203m, 최대 기울기 1.142976도, xy 변위 0.001136m였다. 360개 유효 LiDAR 반환의 최소 1.494346m·최대 4.858143m, 센서 최신성 및 base/lidar TF를 확인했다. clean shutdown·서버 중지 응답은 참, 강제 정리는 거짓이었다. 이는 기존 ROS 로봇 회귀이며 MuJoCo PPO의 Gazebo 배포 검증은 아니다.

## 검증 이력과 범위

초기 실패·통과는 `red.log`·`first_green.log`에 보존했다. 최신 전체 수집 시 병행 작성 중인 12.8의 `test_robust_env.py`가 아직 없는 모듈을 import하여 수집 실패했다. 이 로그는 `green_concurrent_collection_failure.log`로 보존했다. 이를 제외한 당시 12.1~12.6 테스트 109개를 실행했으며 이후 장의 최종 통합 검증은 별도다. Gymnasium 무한 Box 범위 경고 14개와 의도적인 비정상 QVEL 주입 테스트의 MuJoCo 경고가 기록되어 있다.

독립 wheel 증거는 `wheel_build.log`, `wheel_install.log`, `wheel_human.json`, `wheel_viewer.log`, `ctrl_c.log`다. 반복 종료는 `viewer_shutdown_repeat.json`과 `viewer_shutdown.log`, Gazebo는 `gazebo/result.json`과 `gazebo/ch11_tests.log`다. 기계 판독 요약은 `verification_summary.json`에 있다.

희소 몸체 평면 스캔은 전체 장애물 형상을 보지 못한다. 몸체 기울기·낮은 물체·낭떠러지·광선 사이 사각지대가 남는다. 0.8m 안전 비용은 센서 원점 기준이고 로봇 외곽 간격 보장이 아니다. 배치 여유는 전역 경로 존재를 보장하지 않는다. 동적 장애물, 전역 계획, 실물 전이, 장기 학습 회피 성능은 검증 범위 밖이다.


---

## 2026-10-21 편집·코드 2차 리뷰: 원고 12.6 ↔ main 구현

> 범위: 공개 저장소 `main/Ch12` 소스·기존 문서·2026-10-17 실행 증거와 첨부 원고를 정적으로 대조했다. **이번 세션의 실행/PPO 학습/ROS launch 재검증은 수행하지 않았다.** 과거 통과 수치와 새로운 테스트 결과를 혼용하지 않는다. 코드 파일을 수정하지 않는 문서 전용 PR이다.

### 실습 적합성 판정과 위험

**기존 회귀 증거가 있는 실행 경로, 현장 재현과 성능 검증은 조건부.** 심각도는 독자 실습 중 잘못된 입력·기대 성능·안전 오해의 위험 순서다.

1. **[높음·감지 범위]** 실제 구현은 로봇 몸체 평면에 묶인 16/32개의 `mujoco.mj_ray` 광선을 사용한다. 360도 전체 지형 인식이나 낭떠러지 감지를 의미하지 않으며 광선 간 사각지대가 남는다.
2. **[중간·관측 계약]** 기본 16 rays면 48+16=64차원, 32 rays면 80차원이다. 정책 재생 시 num_rays와 manifest가 일치해야 한다. 장애물 미검출 값은 최대 거리/근접도 0으로 정규화된다.
3. **[높음·충돌 정책]** `data.contact`에서 로봇 geom과 활성 장애물 geom 양쪽 순서를 검사하며 물리 하위 스텝의 순간 충돌도 종료 플래그로 유지한다. 충돌 스텝의 총 보상 -100과 성공 보상의 차단을 확인한다.
4. **[중간·성능 한계]** 기존 더미·서브프로세스 PPO 짧은 재생은 저장/읽기 경로만 통과했고 목표 도착률 0%였다. 실용적 회피 성능을 입증하지 않는다.

### 코드/테스트 추적 파일

- [`Ch12/src/quadruped_rl/avoidance_env.py`](../src/quadruped_rl/avoidance_env.py)
- [`Ch12/src/quadruped_rl/models/quadruped_avoidance.xml`](../src/quadruped_rl/models/quadruped_avoidance.xml)
- [`Ch12/tests/test_avoidance_env.py`](../tests/test_avoidance_env.py)
- [`Ch12/scripts/verify_avoidance_env.py`](../scripts/verify_avoidance_env.py)
- 기존 본 보고서의 실험 로그와 [Ch12 README](../README.md). 이 경로는 감사 대상의 **과거 기록**이며 2026-10-21 신규 실행 로그가 아니다.

### 재현 명령 (저장소 루트)

```bash
python -m pytest Ch12/tests/test_avoidance_env.py -q
python Ch12/examples/12_6_avoidance_demo.py --policy random --num-rays 32 --steps 200
MUJOCO_GL=egl python Ch12/scripts/verify_avoidance_env.py --output /tmp/ch12-12-6-review
```

**판정 기준:** 64/80차원, 실제 ray 길이와 정규화, 센서 잡음의 시드 재현성, 로봇/바닥 제외, 장애물 충돌과 낙상을 서로 다른 info 키로 확인한다.

**미검증/후속 조치:** 라이브러리 설치 상태, 본 호스트의 MuJoCo viewer/ROS2 실행과 모델 학습의 재현 여부는 이번 리뷰에서 확인하지 못했다. 실제 수행 후 seed·환경 버전·기준 SHA·stdout·JSON·도표와 실패 여부를 보존하고, 결함이 확인되면 기존 증거를 수정하지 말고 별도 코드 PR을 작성한다.
