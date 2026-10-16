# 12.2절 구현·개선 및 실제 실행 검증 보고서

검증일: 2026-10-17 KST. 대상: `silverbjin/Pysical_AI_ROS2`.
기준 커밋: `b9a60c5` (12.1절). 작업 브랜치: `feat/ch12-section-12-2`.
패키지 버전: `physical-ai-quadruped-rl 0.2.0`.

## 구현 결과

초안의 MJCF·Gymnasium 골격·step·render·환경 테스트를 기존 Ch12 패키지에 통합했다. 새 실습은 `quadruped-rl --section 12.2` 또는 `Ch12/examples/12_2_random_motion.py`로 실행한다. 본문과 같은 `from quadruped_env import QuadrupedEnv`도 설치된 패키지에서 지원한다.

| 초안 또는 기존 상태 | 구현·개선 |
|---|---|
| 외부 STL과 한 관절만 있는 MJCF | 외부 다운로드 없는 완전한 12관절 모델 |
| 모델 코드 복제 우려 | 공통 기구부 XML을 위치·토크 모델이 include |
| 상대 경로 `robot.xml` | 패키지 자산 경로로 읽어 CWD와 무관하게 실행 |
| position과 motor의 의미 불명확 | 두 제어 모드와 각도/토크 스케일을 명시적으로 분리 |
| 각속도 대신 `qvel[:3]` 사용 | 몸체 각속도 `qvel[3:6]`, quaternion wxyz의 31차원 관측 |
| metadata 30 FPS와 실제 제어 50 Hz 불일치 | 제어 간격으로 metadata 계산, 12.2절은 50 Hz |
| reset 노이즈·상태 동기화 생략 | seeded noise, 초기 제어값·이전 행동·시간 초기화, mj_forward |
| `_scale_action`, step 등 생략 | 검증된 행동 변환·실제 물리 계산·항목별 보상·종료 구현 |
| 낙상 높이만 검사, truncated 항상 false | 기울기·몸통 접촉·시간 제한 추가, 프레임 중 낙상 유지 |
| 렌더링 내부 클래스 의존 | MuJoCo 공개 viewer/Renderer, 지연 초기화와 close |
| 무한 루프와 Ctrl+C에서만 close | 유한 스텝·컨텍스트 정리·Ctrl+C 종료 코드 130 |
| 수치 발산 후 엔진 자동 reset 가능 | 상태 및 엔진 BADQPOS/BADQVEL/BADQACC 경고를 오류로 알림 |

12.1절 기본 클래스의 30차원·100 Hz·토크 인터페이스는 유지한다. 새 `QuadrupedTrainingEnv`는 기본 31차원·50 Hz·위치 제어·초기 높이 0.5 m·낙상 높이 0.2 m다. 관절 순서는 fr/fl/rr/rl × hip/thigh/calf를 유지한다.

위치 행동은 명목 자세 `[0, -0.5, 1] rad` 주위 ±0.35 rad로 변환하고 관절 범위를 적용한다. position actuator의 kp는 40/100/100, kv는 2/4/4이며 출력 토크 한계는 20/30/30 N·m다. 에너지 페널티는 목표 각도가 아닌 실제 actuator 출력으로 계산한다. 관절 감쇠 등 수동 힘과 배터리 소비를 모델링한 값은 아니다.

## 구현 중 발견하고 수정한 문제

1. **반발로 낙상을 놓침:** 낮은 몸체를 바닥에 둔 실제 물리 테스트에서 한 제어 프레임 동안 반발로 높이가 회복되어 종료가 누락됐다. 초기 상태 및 각 물리 스텝의 낙상 판정을 유지하도록 수정했다. 수정 전 실패는 `first_green.log`에, 수정 후 통과는 `green.log`에 기록했다.
2. **50 Hz 토크 PD 불안정:** 100 Hz용 외부 PD의 kd 2/4/4를 그대로 적용하면 seed 0/42/123에서 20초 중 각각 2/1/3회 낙상했다. kp/kd 세 후보를 실제 MuJoCo에서 비교하고 kp 40/100/100, kd 2/2/2를 선택했다. 세 시드 모두 20초 무낙상을 회귀 테스트로 고정했다. 내부 position PD는 500 Hz로 동작하므로 외부 PD와 제어 주기가 다르다.
3. **수치 발산 은폐:** 엔진의 자동 초기화 뒤 유한한 배열만 검사하면 발산을 놓칠 수 있다. 사전 상태 검사와 각 물리 스텝의 경고 카운터 검사를 추가했다. 실제 NaN 및 유한하지만 과도한 속도 `1e12`를 넣어 FloatingPointError와 reset 요구를 확인했다.
4. **설치 후 호환 import·include:** wheel에 상위 호환 모듈과 공통 기구부·위치·토크 XML 세 파일을 포함했다. 실제 설치 환경의 site-packages 경로에서 import와 모델 로드를 확인했다.

## 실제 검증 환경과 범위

- Ubuntu-24.04 WSL2/WSLg, Python 3.12.3.
- MuJoCo 3.3.7, Gymnasium 1.2.1, NumPy 2.5.4.
- ROS 2 Jazzy, source 후 Gazebo Sim 8.11.0 (Harmonic).
- 물리 계산, EGL RGB, WSLg viewer를 실제 실행했다. 물리 엔진을 mock으로 대체하지 않았다.
- Linux 가상환경에서 개발 테스트를 실행하고, 별도 가상환경에는 wheel만 설치해 소스 디렉터리 밖 `/tmp`에서 검증했다.

## 테스트 및 반복 실행 결과

| 검사 | 결과 |
|---|---|
| Ch12 전체 pytest | **42개 통과**, skip 0개; 기존 23개와 새 19개 |
| 독립 리뷰 담당 pytest | **42개 통과**, 실제 EGL 포함 |
| Gymnasium checker | 31차원 위치/토크 모두 통과; 기존 30/45차원도 회귀 통과 |
| 12.2절 실제 반복 실험 | 위치/토크 × random/stand × seed 0/42/123 × 1,000 스텝 = 12,000 제어 스텝 |
| 독립 리뷰 반복 실험 | 같은 12,000 제어 스텝 재실행 PASS |
| 12.1절 실제 반복 회귀 | 기존 검증 스크립트의 12,000 제어 스텝 PASS |
| RGB 이미지 | 실제 EGL 640×480 생성, 내용 육안 확인 |
| wheel·viewer | 호환 모듈 import, MJCF include, 실제 viewer 2초 진행과 close PASS |
| Ctrl+C | 실제 viewer CLI 자식 프로세스에 SIGINT, traceback 없이 종료 코드 130 |
| Ch11 회귀·빌드 | 104개 테스트 통과, 두 ROS 패키지 빌드 성공 |
| Gazebo 실제 재실행 | 30초 기립·센서·TF·종료 검증 PASS |

12.2절 반복 실험의 각 실행은 제어 1,000스텝, 물리 20초 분량이다. 위치와 토크의 stand는 세 시드 모두 낙상 0회·시간 제한 1회였다. 위치 stand의 최소 높이는 0.378197 m, 최대 기울기는 1.2217°였다. 토크 stand는 최소 높이 0.364829 m, 최대 기울기 5.2260°였다.

위치 random은 세 시드 모두 낙상 0회·시간 제한 1회였다. 토크 random은 seed 0/42/123에서 각각 56/57/60회 낙상했다. 제한된 위치 PD가 무작위 목표에서도 균형을 유지한 결과와 무작위 토크의 낙상을 구분한다. 어느 경우도 강화학습을 통해 얻은 정책이 아니다. 전체 actuator 출력 최대값은 30 N·m 이하였으며 관절별 한계는 별도 테스트로 확인했다.

## Gazebo 실제 결과

`CH12_GAZEBO_EVIDENCE=Ch12/evidence/section12_2/gazebo`로 실행해 12.1절 증거와 구분했다. 시뮬레이션 8.024~38.046초 구간에서 높이 0.247983~0.249039 m, 최대 기울기 1.267640°, 수평 이동 1.149 mm였다. 실제 모델 관측 1,119개, 관절 상태 32,671개, IMU 3,805개를 수신했고 LiDAR 360개 반환 모두 유효했다.

관측·TF 검사, Gazebo 종료 승인, 정상 프로세스 종료를 통과했으며 강제 정리는 없었다. 기존 Gazebo/ROS 소스 및 종료 스크립트를 변경하지 않았다. 이 검증은 기존 비교 실습의 회귀 검사이며 두 물리 엔진의 동역학 동등성 검증이 아니다.

## 독립 리뷰

별도 검토자가 전체 소스·모델·테스트·가이드·패키징을 검토했다. 쿼터니언 순서와 속도 좌표계, 목표 관절각과 힘 제한, 실제 출력 기반 에너지, 수치 경고와 낙상 유지, 설치 자산을 확인했다. 알려진 PD 문제를 수정한 뒤 전체 테스트 및 실제 반복 실험을 독립 실행했다. 마지막 검토에 추가 조치가 필요한 지적은 없었다. Gazebo 실행은 구현자가 수행했다.

## 남은 제한과 진단

- 31차원은 높이·선속도·접촉 등 일부 정보를 생략한 입문용 관측이다. 충분한 마르코프 상태나 학습 수렴을 보장하지 않는다.
- 보상은 12.1절 기반의 설명 가능한 초깃값이다. PPO 학습·지형 적응·Sim-to-Real·실물 검증은 이번 절의 범위가 아니다.
- PD 기립은 이 모델의 평지·제어 주기에서만 검증했다. 외란 회복과 보행 성능을 뜻하지 않는다.
- Gymnasium checker는 무한 범위 Box에 대해 경고 8개를 출력했다. 수치 오류 음성 테스트의 QVEL 경고 1건은 의도한 고장 주입이다. 정상 반복 실험에서 수치 발산은 없었다.
- Gazebo에는 기존 KDL 루트 관성 경고가 있다. 실제 기립·센서·TF와 프로세스 종료는 별도로 검사했다.
- 12.1절의 과거 증거는 해당 커밋의 기록으로 보존했고, 이번 결과와 코드 해시는 `evidence/section12_2/`에 따로 저장했다.

## 재현 명령과 증거

```bash
python -m pip install -e './Ch12[test,visual]'
CH12_TEST_RENDER=1 MUJOCO_GL=egl python -m pytest Ch12 -q
MUJOCO_GL=egl python Ch12/scripts/verify_training_env.py \
  --output /tmp/12_2_result.json --image /tmp/12_2_frame.png
python Ch12/examples/12_2_random_motion.py --render --steps 1000
# 새 터미널, 학습 가상환경 비활성
CH12_GAZEBO_EVIDENCE=Ch12/evidence/my_12_2_gazebo bash Ch12/scripts/verify_gazebo.sh
```

`red.log`, `first_green.log`, `pd_red.log`, `mujoco_before_pd.*`는 수정 전 실패 기록이다. `pd_tuning.json`은 실제 계수 비교다. 최종 `green.log`, `mujoco.json`, `legacy_mujoco.json`, `reviewer_tests.log`, `reviewer_mujoco.json`, `wheel_human.json`, `frame.png`, `gazebo/result.json`을 최종 판정의 증거로 사용한다. 코드의 LF 정규화 SHA-256은 `source_manifest.json`, 전체 요약은 `verification_summary.json`에 기록한다.
