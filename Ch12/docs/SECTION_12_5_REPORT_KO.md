# 12.5절 목표 이동 환경 구현 및 검증 보고서

2026-10-17, 패키지 0.5.0. 12.4 PPO 도구와 연결되는 QuadrupedGoalEnv를 추가했다.

## 초안에서 개선한 내용

- 거리·헤딩을 몸체 기준으로 계산하고 48차원 관측에 거리/sin/cos를 넣어 각도 경계의 불연속을 줄였다. 쿼터니언 순서와 좌표계 부호를 명시했다.
- 전용 MJCF에 충돌 비활성 목표 mocap을 추가했다. 이름으로 mocap ID를 조회하고 시드 기반 목표 샘플링과 고정 목표 API를 구현했다.
- 보상을 계산하는 중 목표를 변경하지 않는다. 기존 목표 보상과 도착 사건을 확정한 후 새 목표·기준 거리·반환 관측을 함께 갱신한다. 낙상 시 진행·도착 보상을 차단한다.
- 직진 속도 보상을 제거하고 진척도·도착·자세·실제 토크·행동 변화·비발 접촉·낙상 항목을 제공한다. 거리 감소식을 엄밀한 할인 potential shaping과 구분했다.
- resample 학습과 terminate 평가를 구분한다. 목표·거리·도착 사건·에피소드 누계를 info와 CSV에 기록한다.
- 공개 user_scn/mjv_initGeom으로 최근 5초·최대 256점 경로를 RGB와 실제 viewer에 표시한다. reset 시 제거하고 CSV 그래프는 에피소드 사이를 연결하지 않는다.
- 이미지 검사에서 기존 고정 카메라에 목표가 보이지 않음을 발견했다. 로봇과 목표의 중간을 보는 자동 카메라로 수정하고, 앞·뒤 목표 모두 빨간 마커가 실제 픽셀에 나타나는 회귀 검사를 추가했다.

## 검증 결과와 범위

위치 제어, 정지/무작위, 목표 거리 1m 및 2~3m, terminate/resample, 시드 0/42/123 조합의 24회 × 1,000스텝 실제 MuJoCo 검증 PASS. 기립 baseline 낙상 0, 토크 한계 30Nm 이하, 관측·보상 유한값과 합계·목표 전환 기준 거리 검사 PASS. 마커를 로봇과 겹쳐도 기존 환경과 qpos/qvel이 동일함을 테스트했다.

실제 wheel에서 저장 PPO를 불러와 human viewer 100스텝을 진행했다. 경로 geometry 최대 101개, viewer 정상 종료, CLI SIGINT 종료 코드 130을 확인했다. RGB 이미지와 경로 그래프를 직접 확인했다.

마지막 반복 검증에서 MuJoCo 3.3.7 뷰어의 비동기 close와 GLFW 프로세스 종료 정리가 충돌하는 간헐적 종료 코드 -6을 발견했다. 실제 실패를 기록하고, 렌더 객체 소멸 완료까지 최대 5초 대기하도록 수정했다. 공개 is_running은 종료 요청만 확인하므로 완료 신호가 아니다. 고정 버전의 Handle._sim weakref를 한 곳에서만 사용하는 호환 처리이며 MuJoCo 버전 변경 시 재검증이 필요하다. 12.1/12.2/12.3/12.5 각각 정상 종료 1회와 실제 SIGINT 2회, 총 12개 별도 프로세스가 모두 정상 종료했다.

실제 Gazebo 8.11.0 / ROS 2 Jazzy에서 기존 Ch11 패키지 2개 빌드와 104개 테스트를 통과했다. 8.024~38.046초 시뮬레이션 관측에서 몸체 높이 0.24798~0.24904m, 최대 기울기 1.26718도, 변위 0.00115m, LiDAR 360개 유효 반환과 센서·TF를 확인했다. 서버 종료 응답과 정상 종료 PASS. Gazebo 결과는 기존 ROS 로봇의 회귀 검증이며 PPO를 Gazebo에서 실행한 결과는 아니다.

독립 리뷰의 두 결함을 수정한 최종 통합 테스트 90개와 독립 리뷰 테스트 90개가 통과했다. 최종 wheel에서도 카메라·종료 변경 후 viewer·Ctrl+C 재검증을 통과했다. 로그·수치·화면은 `evidence/section12_4`, `evidence/section12_5`에 있다. Gymnasium 무한 Box 경고, 의도적인 비정상 QVEL 주입 경고, 기존 KDL 경고는 구분해 기록했다.

짧은 goal PPO 실험은 도착률 0%였다. 이 결과로 목표 이동 능력이 완성되었다고 주장하지 않는다. 자동 커리큘럼·단계 간 학습 재개·장애물 회피·Sim-to-Real은 구현 범위에 포함하지 않는다. 사용자는 가이드의 긴 학습 명령과 별도 다중 시드 평가로 성능을 확인해야 한다.


---

## 2026-10-21 편집·코드 2차 리뷰: 원고 12.5 ↔ main 구현

> 범위: 공개 저장소 `main/Ch12` 소스·기존 문서·2026-10-17 실행 증거와 첨부 원고를 정적으로 대조했다. **이번 세션의 실행/PPO 학습/ROS launch 재검증은 수행하지 않았다.** 과거 통과 수치와 새로운 테스트 결과를 혼용하지 않는다. 코드 파일을 수정하지 않는 문서 전용 PR이다.

### 실습 적합성 판정과 위험

**기존 회귀 증거가 있는 실행 경로, 현장 재현과 성능 검증은 조건부.** 심각도는 독자 실습 중 잘못된 입력·기대 성능·안전 오해의 위험 순서다.

1. **[높음·원고 교정]** 12.3의 locomotion 관측과 12.5의 goal 관측은 둘 다 48차원이지만 9:12 인덱스 의미가 다르다. goal은 `distance,sin(heading),cos(heading)`이고 목표 좌표를 단순히 2차원 추가한 47차원 모델이 아니다. 정책 파일 혼용 금지.
2. **[중간·보상 용어]** 구현의 `50 × (prev_dist − curr_dist)`는 할인율 `gamma<1`에서 엄밀한 정책 불변 potential-based shaping을 보장하는 식이 아니다. 개발 주석도 단순 진척도 shaping으로 구분한다.
3. **[중간·전이/평가]** 현재 목표 보상을 계산한 뒤 도착 이벤트를 기록하고 새 목표로 resample한다. 반환 관측의 목표와 `evaluated_target`의 목표가 다른 것이 정상이다. 평가에서는 목표에 도착하면 terminate 모드를 사용한다.
4. **[중간·실습 한계]** 기존 짧은 PPO 증거의 도착률은 0%다. 자동 80% 성과 승급·장기 목표 도착은 구현/입증했다고 안내하지 않는다.

### 코드/테스트 추적 파일

- [`Ch12/src/quadruped_rl/goal_env.py`](../src/quadruped_rl/goal_env.py)
- [`Ch12/src/quadruped_rl/ppo.py`](../src/quadruped_rl/ppo.py)
- [`Ch12/config/section12_5_goal.json`](../config/section12_5_goal.json)
- [`Ch12/tests/test_goal_env.py`](../tests/test_goal_env.py)
- 기존 본 보고서의 실험 로그와 [Ch12 README](../README.md). 이 경로는 감사 대상의 **과거 기록**이며 2026-10-21 신규 실행 로그가 아니다.

### 재현 명령 (저장소 루트)

```bash
python -m pytest Ch12/tests/test_goal_env.py -q
quadruped-goal --policy stand --target 2 1 --steps 200 --seed 42
MUJOCO_GL=egl quadruped-goal --policy stand --target 2 1 --steps 200 --frame-path /tmp/ch12-12-5-frame.png --trajectory-path /tmp/ch12-12-5-path.csv
python Ch12/scripts/plot_trajectory.py /tmp/ch12-12-5-path.csv --output /tmp/ch12-12-5-path.png
```

**판정 기준:** 48차원 의미, 몸체 오른쪽 목표의 음수 헤딩, sin/cos 연속성, `is_success`·`goals_reached`·`target`·`evaluated_target`을 구분한다. 목표로 걷는 능력은 학습과 분리해 평가한다.

**미검증/후속 조치:** 라이브러리 설치 상태, 본 호스트의 MuJoCo viewer/ROS2 실행과 모델 학습의 재현 여부는 이번 리뷰에서 확인하지 못했다. 실제 수행 후 seed·환경 버전·기준 SHA·stdout·JSON·도표와 실패 여부를 보존하고, 결함이 확인되면 기존 증거를 수정하지 말고 별도 코드 PR을 작성한다.

---

## 2026-10-21 후속 코드 수정·정적 점검 (이전 문서 전용 리뷰 이후)

이 문서 상단의 **「코드 변경 없음 / 문서 전용 PR」**은 최초 편집·코드 2차 리뷰 시점의 기록으로 보존한다. 이후 동일한 기존 절별 브랜치에 실제 **코드 보강과 신규 회귀 테스트**를 추가했다. 변경 목록, 정적 검증 범위와 `NOT_RUN` 항목은 [SECTION_12_5_FIX_TEST_REPORT_KO.md](SECTION_12_5_FIX_TEST_REPORT_KO.md)를 우선 참조한다. 기존 2026-10-17 런타임 PASS는 새로운 커밋의 실행 증거가 아니다.
