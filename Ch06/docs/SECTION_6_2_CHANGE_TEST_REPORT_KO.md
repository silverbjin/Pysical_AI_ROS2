# SECTION 6.2 — KDL 솔버 설정 수정 및 정적 테스트 기록

- 기준: 기존 `feat/ch06-section-6-2`에 후속 반영. 코드 리뷰 `SECTION_6_2_REPORT_KO.md`.
- 변경: `kinematics.yaml`의 KDL 유지, timeout 0.005→0.05s, **5축 관절 체인에 position_only_ik: true** 명시. XYZ 위치 목표 실습에 맞추되 **말단 자세(roll/pitch/yaw) 요구를 무시하는 교육용 모드**이다.
- 추가: `scripts/audit_solver_config.py` (Python 표준 라이브러리 기반 SRDF 그룹, 5개 조인트, `base_link→link_wrist`, YAML 플러그인 이름·타임아웃·position-only 계약 검사).
- 테스트: `tests/test_section_6_2.py`에 정상 계약·그룹 누락·잘못된 timeout·tip mismatch 회귀 케이스 4개.
- 소스 계약/정적 점검: 필수 config 키, 검사기 주요 분기, 4개 회귀 테스트 정의 검증 PASS.
- ROS 2 Jazzy 플러그인 로딩 및 IK 실제 성공률: **NOT_RUN**. Trac-IK 우수성·성공률은 주장하지 않음.
- 로컬 재실행:
  ```bash
  python3 -m py_compile Ch06/scripts/audit_solver_config.py Ch06/tests/test_section_6_2.py
  python3 Ch06/scripts/audit_solver_config.py
  python3 -m unittest discover -s Ch06/tests -p 'test_section_6_2.py' -v
  ```
- 알려진 한계: 원격 이외 검증환경에서 전체 모듈 `py_compile`/unittest 실측 증거는 이 기록에 포함되지 않으므로 **SYNTAX_PASS나 RUNTIME_PASS 아님**. 실제 IK 해/방향 제약/관절 한계는 이후 통합 시험 필요.
- 참고 근거: MoveIt 2 KDL 플러그인의 `position_only_ik` 처리 및 MoveIt kinematics configuration 공식 문서.
