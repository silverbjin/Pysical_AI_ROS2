# SECTION 6.1 — 코드 수정 및 정적 테스트 보고서

- 기준 브랜치: `feat/ch06-section-6-1` (기존 브랜치에 후속 커밋).
- 근거: 기존 `SECTION_6_1_REPORT_KO.md`, 수치 IK 원고, `Ch06/1_simple_ik_concept.py`.
- 코드 변경: `pinv`를 DLS 정칙화로 대체, 변화량 제한(0.25 rad/step), 비유한 입력/매개변수 검사, 기하학적 작업 영역 거부, FK 잔차 측정, 반복 상한 실패를 명확히 분기.
- 호환성: 함수 이름·위치 인자·성공 시 numpy 관절 각도 배열·실패 시 None 반환 유지. 새로운 키워드 매개변수만 선택적으로 추가.
- 정적 점검: 소스 계약 검사(함수명/작업영역/정칙화/잔차 기준/테스트 5건 정의) PASS. 수학적 참조값을 독립적인 2링크 계산으로 대조함.
- 이 세션의 CPython 직접 실행: **NOT_RUN** (GitHub 연결을 통한 수정과 로컬 실행 파일의 직접 공유 불가).
- 테스트 명령(ROS 불필요):
  ```bash
  python3 -m pip install numpy
  python3 -m py_compile Ch06/1_simple_ik_concept.py Ch06/tests/test_section_6_1.py
  python3 -m unittest discover -s Ch06/tests -p 'test_section_6_1.py' -v
  ```
- 예상 Acceptance: reachable FK 오차 <1mm; out-of-reach/비수렴은 성공 처리하지 않음; Jacobian 중앙차분 일치; NaN 입력 거절.
- 물리/ROS 실행: **NOT_RUN**. 2축 수치 예제는 관절 한계·충돌·속도 안전성을 구현하지 않으므로 실제 모터 명령으로 사용 금지.
- 검토 미해결: 애니메이션 예제 2/3은 기존 `pinv` 구현을 유지한다. 이 예제와 본 개정 코드의 결과 차이는 교재에서 대비하여 설명할 것.
