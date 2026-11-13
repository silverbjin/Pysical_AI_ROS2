# Ch06 §6.7 — 원본 2축 IK 실패 재현 및 DLS 비교 공개 CI 인수 기록

> 인수일: 2026-11-13 KST. 이 파일은 기존 `SECTION_6_7_REPORT_KO.md`의 2026-10 **정적 검토**와 구별되는 새 실측 증거이다. ROS MoveIt IK, Gazebo, GUI 및 실물 로봇 인수 결과가 아니다.

## 검수 결과

**검수 대상:** 원본 `Ch06/4_divergence.py` 내 `Planar2DOF`의 Jacobian, FK, 직접 역행렬 기반 IK. GUI 부작용 없이 원본 class AST만 추출해 실제 함수를 실행했다. 원본 소스는 수정하지 않았고 SHA256 `3aecf94f77fbecce8668c5364ac4fab7394a5cb6da53077efa027ff85933d706`를 검증했다.

| 실험 | 입력 | 관측/판정 |
|---|---|---|
| 정확한 특이점 | θ=(0,0), 목표 (1.8,0.2)m | `det(J)=0.0`, 최소 특잇값 `0.0`, 원본 `Divergence (Singularity!)` 재현 **PASS** |
| 특이점 근접 폭발 | θ=(0,0.001)rad, 동일 목표 | 원본 직접 역행렬 `Divergence (Explosion!)`, 한 번의 실제 계산 각도 점프 `223.4727200951rad` — 오류 재현 **PASS** |
| DLS 수치 비교 | θ=(0,0)rad, 목표 (1.8,0.2)m | **비교 전용** DLS(damping=0.15, alpha=0.5), 15회 반복, 오차 `0.00067213684m`, 최대 업데이트 `0.150000rad`, **PASS** |
| 서로 다른 두 IK 해 | 목표 (1,1)m | elbow-up/down의 원본 FK 최종 오차 각각 `0m` **PASS** |
| 도달 불가능 목표 | 목표 (2.2,0.2)m, 최대 사거리 2m | 사전 `UNREACHABLE_REJECTED`, 구동 명령 없음 **PASS** |
| 실제 교재 Xacro | `Ch06/my_robot.urdf.xacro` | 5개 revolute 관절의 lower/upper/velocity 존재·유효성 **PASS** |

### 공개 GitHub Actions 원본 증거

- PR: [#156](https://github.com/silverbjin/Pysical_AI_ROS2/pull/156).
- GitHub Actions: [Run #43405940935](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43405940935) — **SUCCESS**.
- 원본 Artifact: [#14027975325](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43405940935/artifacts/14027975325) (`receipt.json`, `original_numeric.log`, `independent_audit.log`, `pip_freeze.txt`, `checkout_sha.txt`).
- CI checkout SHA: `32fd3055e1c1235f1020e259e0071ea70f0bed13` (PR synthetic merge ref); 테스트 대상 소스 브랜치 SHA: `82bd5fe110bc1a3c513828729ff1f79fe2d548b0` (문서 보고서 추가 전).
- 원본 수치 성공 로그: `CH06_67_ORIGINAL_IK_FAILURE_AND_TEST_ONLY_RECOVERY_SCOPED_PASS`.
- 독립 영수증 감사: `CH06_67_INDEPENDENT_BOOK_SOURCE_HASH_FAILURE_AND_DLS_RECEIPT_PASS`.
- 실행 환경: Python 3.12, NumPy 2.2.6, Ubuntu GitHub Actions, ROS/Gazebo/Docker 실행 없음.

## 해석과 작업 경계

**인수:** 원본 2축 IK의 특이점·폭발 오류를 실제 수치로 재현했고, 원본을 변경하지 않은 상태에서 별도 DLS 대조 실험의 개선을 검증했다. 원본 모델의 5축 URDF 조인트 제한도 정적 파일을 파싱하여 확인했다.

**아직 미검증:** 원본 Matplotlib 슬라이더의 실행/롤백 GUI, ROS 2 MoveIt PlanningScene에서의 실제 IK 회복, 충돌 검사, 관절 실제 속도·토크·안전 정지, 실물 하드웨어와 정상 MoveItPy 소멸자 경로. DLS 비교 코드를 원본 IK 구현이나 하드웨어 제어기로 사용해서는 안 된다.

이미 PASS한 Ch06 §6.4 Pose IK, §6.5 Pilz LIN [CI #43344842325](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43344842325), §6.6 MoveIt→Gazebo [CI #43347410213](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43347410213) 은 **NOT_RERUN**.

Ch07 §7.2 원본 RGB-D/OGRE2 Issue #127 **BLOCKED**, Ch10 Issue #123 **HOLD**, Ch11 Issue #130 별도 원본 SaveMap 문제 유지. 교재 전체 101개 절의 완전 인수를 주장하지 않는다.
