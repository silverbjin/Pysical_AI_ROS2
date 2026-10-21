# SECTION 6.7 — 특이점/관절 제한 진단 예제 구현 및 정적 테스트 보고서

- 기존 브랜치: `feat/ch06-section-6-7`.
- 기존 6.7 원고는 일부 API 예시만 있고 실습 코드는 완결되어 있지 않음. 고의 발산 시연 `4_divergence.py`를 실제 안전 제어기로 '수정'하지 않고, **안전한 비교 진단 도구** `Ch06/5_ik_safety_diagnostics.py`를 신규 추가.
- 새 모듈: Jacobian 최소 특이값/조건수, 기하학적 도달성, DLS(λ>0), 스텝 L2 노름 제한, 관절 각도 상하한을 표준 Python 수학으로 계산하고 JSON 출력. 실제 모터 명령/ROS 실행은 없음.
- 주요 상태: `UNREACHABLE`, `NEAR_SINGULAR`, `STALLED`, `STEP_COMPUTED`. 계산 한 스텝의 결과일 뿐 완성 IK/경로/물리 안전 증명은 아님.
- 테스트: `Ch06/tests/test_section_6_7.py`에 완전 펴진 특이점, 작업영역 밖 목표, 관절 변화량 제한, 관절 범위 유지, 비유한 입력 거절 5개.
- 원격 코드 정적 계약 검사(함수·상태·DLS·하한·test fixture 선언) PASS. CPython `py_compile` 및 unittest 실제 실행, ROS/MoveIt 및 Gazebo 회귀: **NOT_RUN**.
- 실행 예:
  ```bash
  python3 -m py_compile Ch06/5_ik_safety_diagnostics.py Ch06/tests/test_section_6_7.py
  python3 -m unittest discover -s Ch06/tests -p test_section_6_7.py -v
  python3 Ch06/5_ik_safety_diagnostics.py --joint 0 0 --target 0.7 0
  python3 Ch06/5_ik_safety_diagnostics.py --joint 0.1 0.1 --target 1.2 0
  ```
- 남은 연구 항목: 실제 MoveIt의 `Constraints`/API 호출과 Planning Scene 통합, 케이블 충돌 모델, 시간 통계(P95/P99), joint speed/effort 제약, 5축 arm 전체 모델의 IK 및 controller feedback 검증.
- 안전 주의: 관절 범위 `[-π,π]`는 **교육용 기본 예시**다. Ch06 실제 URDF의 각 joint별 제한과 동일하지 않으므로 물리 장치에 직접 적용해서는 안 된다.
