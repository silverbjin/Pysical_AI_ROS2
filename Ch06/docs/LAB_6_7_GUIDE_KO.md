# 6.7절 실습 가이드 — 고장 재현 → 원인 분리 → 해결책 평가

> 기준일 2026-10-20 KST | 기준 main `1b9e8215e213` | 첨부 원고 6.7절 | Ubuntu 24.04 · ROS 2 Jazzy · MoveIt 2
> 판정 수준: **정적 검토**. 실제 ROS 2/WSLg/Gazebo 실행·테스트 로그가 이 작업에는 없으므로 동적 검증은 미수행/미검증으로 표시한다.
> 원본 경로: https://github.com/silverbjin/Pysical_AI_ROS2/tree/1b9e8215e2130c492969bb0da52a82e707c3a16f/Ch06

## 목표
역운동학 실패를 '알고리즘 문제'로 단정하지 않고 **관측 → 가설 → 최소 재현 → 계측 → 수정안 비교 → 회귀검증** 단계로 진단한다. **ROS 실제 하드웨어 연결 금지**; 개념 실험은 2축 Python, 로봇 실험은 유효성 확인된 mock/Gazebo에서만.

## 준비 (시각화용, ROS 불필요)
```bash
cd ~/Pysical_AI_ROS2
python3 -m venv /tmp/ch06-ik-debug
source /tmp/ch06-ik-debug/bin/activate
pip install numpy matplotlib
python3 Ch06/4_divergence.py
```
슬라이더의 목표/초기 각/alpha를 바꾸며 `Converged`와 `Divergence` 및 rollback을 비교한다.

## 장애별 검증 과제
| 실험 | 재현 방법 | 원인 확정에 필요한 evidence | 개선안 |
|---|---|---|---|
| A 특이점 | 2축 팔을 직선으로 펴고 기준 축방향 목표를 요구 | `det(J)`, 최소 singular value, 각도 갱신량, 오차 로그 | DLS/최대 각도 스텝/목표 offset 비교 |
| B 다중 해 | 같은 목표에 elbow-up/down seed 두 개 사용 | 결과 각도, 중간 joint jump, 동일 FK 결과 | seed continuity 및 joint limits 사용 |
| C 관절 한계 | 제한 근처의 목표를 정의 | URDF `lower/upper`, 계획 목표, 컨트롤러 거부 여부 | 유효 목표 수정; 기계 한계를 삭제하지 않기 |
| D 충돌 | Planning Scene에 장애물 모델 배치 | contact pair, ACM 항목, path sampling | collision geometry 및 tool/cable envelope 개선 |
| E 시간 제약 | 10~100회 같은 목표 planning 반복 | 평균·P95/P99 latency, timeout·실패율, 센서 staleness | 속도 요구에 맞게 solver/planner/Servo 선택 |

## MoveIt 환경을 이용한 심화 검증
6.3~6.6절의 URDF 로딩, 계획 파이프라인, 컨트롤러 준비가 모두 해결된 뒤에만 진행한다. `moveit_configs_utils`와 `moveit_py` 호출 패턴은 공식 [Python planning tutorial](https://github.com/moveit/moveit2_tutorials/blob/main/doc/examples/motion_planning_python_api/motion_planning_python_api_tutorial.rst)을 대조한다. 원고의 `get_current_state()`나 `set_path_constraints()` 예시는 함수 제공 여부·호출 형식이 확인되기 전 복사 실행하지 않는다.

## 보고서 작성 템플릿
```text
실험 ID: IK67-A
현상/스크린샷:
재현 조건: model SHA, seed, 목표 pose, 초기 joint, solver timeout
관측: residual(m), min singular value, max |Delta theta|(rad), planning time(ms)
가설 1/2/3:
원인 확정 근거:
후보 조치 A/B와 실패율, 경로 안전성 비교:
선정 이유:
회귀 결과: PASS / FAIL / NOT RUN
```

## Acceptance
- 물리/제어 안전 설정을 우회하지 않고, 목표 오차·관절 한계·충돌·controller result·latency를 별도로 판단.
- 시뮬레이터 실행 결과가 없다면 '재현 미검증'으로 남김.
- IK 알고리즘의 수렴과 물리 실행 성공을 같은 용어로 혼용하지 않음.

**핵심 교훈:** 빠르게 푼 IK가 곧 안전한 경로는 아니며, 특이점·케이블·관절 한계는 모델과 제어기의 공동 책임이다. [보고서](SECTION_6_7_REPORT_KO.md).
