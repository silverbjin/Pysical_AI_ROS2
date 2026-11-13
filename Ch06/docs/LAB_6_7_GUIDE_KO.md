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

---

## 2026-11 — 실측 수치 진단: 원본 Planar2DOF 실패를 재현하는 CI

기존 위 가이드는 2026-10 당시 **정적 검토 이력**이다. Ch06 §6.4 Pose IK, §6.5 Pilz LIN, §6.6 MoveIt→Gazebo 실제 인수는 이미 별도로 통과했으므로 이 절에서 중복 실행하지 않는다. 새 검수는 `Ch06/4_divergence.py`에 실제 포함된 **원본 Planar2DOF** 수치 계산만 확인한다.

### 한 번에 실행

~~~bash
cd ~/Pysical_AI_ROS2
python3 -m venv /tmp/ch06-67-numeric
source /tmp/ch06-67-numeric/bin/activate
pip install 'numpy==2.2.6'
python ci/ch06_67_numeric_diagnostics_once.py
python ci/ch06_67_verify_receipt.py \
  ci-results/ch06-67/receipt.json Ch06/4_divergence.py
python3 -m json.tool ci-results/ch06-67/receipt.json
~~~

관찰 파일은 `ci-results/ch06-67/receipt.json`이다. 원본 Python을 GUI로 import하면 Matplotlib 슬라이더/애니메이션이 열릴 수 있어, 이번 독립 수치 검수는 Python AST에서 **원본 Planar2DOF 클래스만 추출해 그대로 실행**한다. 학습자의 원본 `4_divergence.py`를 변경하지 않는다.

### 기대 결과와 논리적인 원인 분리

1. **정확한 특이점**: 1m×2링크가 완전히 펼쳐진 θ=(0,0)에서 J의 det와 최소 특잇값이 0이며, 원본 inverse_kinematics_history가 `Divergence (Singularity!)`를 보고한다.
2. **특이점 근접 폭발**: θ=(0,0.001)rad의 자코비안 직접 역행렬 업데이트가 과도한 관절 점프를 만들어 `Divergence (Explosion!)`가 발생한다. 실제 joint command는 전송하지 않는다.
3. **별도의 수치 비교**: 테스트 내부에서만 DLS(damping=0.15, alpha=0.5, 단일 스텝 norm≤0.15rad)를 사용해 목표 (1.8,0.2)m 오차 <0.001m에 수렴하는지 비교한다. **이는 원본 IK 알고리즘이 수정됐다는 뜻이 아니며, 실물 제어에 승인된 solver도 아니다.**
4. **다중 해와 도달 가능성**: (1,1)m을 만드는 elbow-up/down 두 관절 해를 실제 원본 FK로 비교하고, 최대 도달 거리 2m를 벗어난 (2.2,0.2)m는 목표를 거부한다.
5. **실제 교재 모델의 한계**: 별개로 Ch06 5축 Xacro의 revolute limit와 velocity 값 5개를 파일에서 검증한다. 2D 1m×2링크 교육 예제와 5축 ROS 로봇 모델을 같은 기구학이라고 해석하지 않는다.

예상 마커(실제 수치·성공 여부는 공개 CI 로그 확인):

~~~text
CH06_67_ORIGINAL_JACOBIAN_SINGULARITY_REPRODUCED_PASS
CH06_67_ORIGINAL_INVERSE_EXPLOSION_REPRODUCED_PASS
CH06_67_DLS_BOUNDED_NUMERIC_RECOVERY_PASS ...
CH06_67_TWO_DISTINCT_SEEDS_SAME_FORWARD_KINEMATICS_PASS
CH06_67_UNREACHABLE_GOAL_REJECTED_WITHOUT_ACTUATION_PASS
CH06_67_ORIGINAL_FIVE_JOINT_LIMITS_IN_SOURCE_XACRO_PASS
CH06_67_ORIGINAL_IK_FAILURE_AND_TEST_ONLY_RECOVERY_SCOPED_PASS
CH06_67_INDEPENDENT_BOOK_SOURCE_HASH_FAILURE_AND_DLS_RECEIPT_PASS
~~~

### 판정 범위와 제외 조건

- 공개 workflow: `.github/workflows/book-ch06-67-ik-diagnosis.yml`
- 전용 실행기: `ci/ch06_67_numeric_diagnostics_once.py`
- 독립 원본 SHA·수치 증거 검사: `ci/ch06_67_verify_receipt.py`
- **PASS 가능 범위:** 원본 Jacobian 기반 IK의 특이점/폭발 재현과 실험용 DLS의 유한·제한 스텝 수치 비교, 실제 Ch06 Xacro joint limits.
- **NOT_RUN:** Matplotlib GUI 슬라이더·롤백 시각화, MoveItPlanningScene 충돌/실행, 실제 ROS 기구학, 실물 로봇, Ch10.
- Ch07 §7.2 원본 OGRE2 카메라 Image/CameraInfo는 기존 #127 **BLOCKED**, Ch10 #123 **HOLD**를 보존한다.
